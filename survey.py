# -*- coding: utf-8 -*-
#
#    This file belongs to the ICTV project, written by Nicolas Detienne,
#    Francois Michel, Maxime Piraux, Pierre Reinbold and Ludovic Taffin
#    at Universite Catholique de Louvain.
#
#    Copyright (C) 2017  Universite Catholique de Louvain (UCL, Belgium)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import web
from urllib.parse import urlparse

from pyquery import PyQuery

from ictv.ORM.channel import Channel
from ictv.plugin_manager.plugin_capsule import PluginCapsule
from ictv.plugin_manager.plugin_manager import get_logger
from ictv.plugin_manager.plugin_slide import PluginSlide
from ictv.plugin_manager.plugin_utils import MisconfiguredParameters
import json
from pprint import pprint


def get_content(channel_id):
    #From the configuration file
    channel = Channel.get(channel_id)
    logger_extra = {'channel_name': channel.name, 'channel_id': channel.id}
    logger = get_logger('survey', channel)
    question = channel.get_config_param('question')
    author = channel.get_config_param('author')
    answers = channel.get_config_param('answers')
    secret = channel.get_config_param('secret')

    if not question or not answers:
        logger.warning('Some of the required parameters are empty', extra=logger_extra)
        return []

    #For the .json
    current_question_entry = None
    try:
        with open('./plugins/survey/survey_questions.json', 'r') as data_file:
            saved_data = json.load(data_file)
    except:
        saved_data = {
            "questions": [create_new_question_entry(channel_id, question, answers)]
        }

        percent_votes = [None]*len(answers)
        current_question_entry = saved_data["questions"][-1]
    else:
        #Check that the .json file is valid
        if not is_json_valid(saved_data):
            raise SyntaxError("The JSON file of the ICTV survey has an invalid syntax.")

        current_question_entry = find_question_entry(saved_data, channel_id)
        if current_question_entry != None:
            #Check if the .json is up-to-date with the configuration
            if not is_json_up_to_date(answers, current_question_entry["answers"]):
                current_question_entry["question"] = question
                current_question_entry["totalVotes"] = 0
                updated_answers = [None]*len(answers)
                i = 0
                for answer in answers:
                    updated_answers[i] = {
                        "answer": answer,
                        "votes": 0
                    }
                    i += 1
                current_question_entry["answers"] = updated_answers
        else: #the question was not contained in the .json file
            new_question_entry = create_new_question_entry(channel_id, question, answers)
            if len(saved_data["questions"]) == 0:
                new_question_entry["id"] = 1
            else:
                new_question_entry["id"] = saved_data["questions"][-1]["id"] + 1
            saved_data["questions"].append(new_question_entry)
            current_question_entry = new_question_entry

        #Compute the percentage for each answers
        percent_votes = compute_percent_votes(current_question_entry["answers"], current_question_entry["totalVotes"])

    with open('./plugins/survey/survey_questions.json', 'w') as towrite: # TODO : make flexible
        json.dump(saved_data, towrite, indent=4)

    return [SurveyCapsule(question, author, answers, percent_votes, secret, channel_id, current_question_entry["id"])]

def is_json_valid(json_data):
    """ Check if the .json file contains valid syntax for a survey """
    try:
        if json_data == None:
            return False
        if json_data["questions"] == None:
            return False
        for question in json_data["questions"]:
            if question["question"] == None:
                return False
            if question["channel"] == None:
                return False
            if question["id"] == None:
                return False
            if question["totalVotes"] == None:
                return False
            if question["answers"] == None:
                return False
            for answer in question["answers"]:
                if answer["answer"] == None:
                    return False
                if answer["answer"] == None:
                    return False
        return True
    except (TypeError, KeyError):
        return False

def create_new_question_entry(channel_id, question, answers):
    """ Creates a new entry for a question in the .json file (with id=1) and returns it """
    new_question_entry = {
    "id": 1,
    "channel" : channel_id,
    "question": question,
    "totalVotes":0,
    "answers" : []
    }

    for answer in answers:
        answer_entry = {
        "answer": answer,
        "votes": 0
        }

        new_question_entry["answers"].append(answer_entry)

    return new_question_entry

def find_question_entry(json_data, channel_id):
    """
        Find the question entry in the data of the .json file
        Returns the dictionary that represents the question or @None if it wasn't found
    """
    for question in json_data["questions"]:
        if question["channel"] == channel_id:
            return question
    return None

def is_json_up_to_date(config_answers, saved_answers):
    #config_answers is a list of strings
    #saved_answers is a list of dictionary with a key "answer" and a key "votes"
    if not len(config_answers) == len(saved_answers):
        return False
    else:
        if are_answers_updated(config_answers, saved_answers):
            return False
    return True

def are_answers_updated(config_answers, saved_answers):
    #config_answers is a list of strings
    #saved_answers is a list of dictionary with a key "answer" and a key "votes"
    for saved_answer in saved_answers:
        if saved_answer["answer"] not in config_answers:
            return True
    return False

def compute_percent_votes(saved_answers, total_nb_votes):
    """ Compute the percentage of answer for each answer """
    if total_nb_votes == 0:
        return None

    percent_votes = []
    for answer in saved_answers:
        percent_votes.append((answer["votes"]/total_nb_votes) * 100)

    return percent_votes

class SurveyCapsule(PluginCapsule):
    def __init__(self, question, author, answers, percent_votes, secret, channel_id, question_id):
        self._slides = [SurveySlide(question, author, answers, percent_votes, secret, channel_id, question_id)]

    def get_slides(self):
        return self._slides

    def get_theme(self): #TODO : change that ?
        return None

    def __repr__(self):
        return str(self.__dict__)

class SurveySlide(PluginSlide):
    def __init__(self, question, author, answers, percent_votes, secret, channel_id, question_id):
        self._duration = 10000000
        self._content = {'title-1': {'text': question}, 'text-0': {'text': author}}

        self._content['nb-answers'] = len(answers)
        i = 1
        for answer in answers:
            self._content['text-'+str(i)] = {'text': answer}
            self._content['image-'+str(i)] = {'qrcode': web.ctx.homedomain+'/channel/'+str(channel_id)+'/result/'+str(question_id)+'/'+str(i)}
            i += 1

        if secret:
            self._content['show-results'] = False
            self._content['no-votes'] = None #no information about this
        else:
            if percent_votes == None:
                self._content['show-results'] = False
                self._content['no-votes'] = True
            else:
                self._content['show-results'] = True
                self._content['no-votes'] = False
                self._content['percent-votes'] = percent_votes

    def get_duration(self):
        return self._duration

    def get_content(self):
        return self._content

    def get_template(self) -> str:
        #if self._nb_answers == 1:
        #    return 'template-survey-1-answer'
        #return 'template-survey-'+str(self._nb_answers)+'-answers'
        return 'template-survey'

    def __repr__(self):
        return str(self.__dict__)
