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
    #from the configuration file
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
    current = {
        "id": 1,
        "channel" : channel_id,
        "question": question,
        "totalVotes":0,
        "answers" : []
    }

    for e in answers:
        curr = {
            "answer": e,
            "votes": 0
        }

        current["answers"].append(curr)
    try:
        data_file = open('./plugins/survey/survey_questions.json', 'r')
        data = json.load(data_file)
        data_file.close()
    except:
        data = {
            "questions": [current]
        }
    else:
        found = False
        current_index = 0
        for e in data["questions"]:
            if e["channel"] == channel_id:
                found = True
                #Check if the .json is up-to-date with the configuration
                same_nb_answers = (len(answers) == len(data["questions"][current_index]["answers"]))
                updated = False
                if not same_nb_answers:
                    updated = True
                else:
                    if are_answers_updated(answers, data["questions"][current_index]["answers"]):
                        updated = True
                print(same_nb_answers)
                print(updated)
                if updated:
                    data["questions"][current_index]["question"] = question
                    data["questions"][current_index]["totalVotes"] = 0
                    updated_answers = [None]*len(answers)
                    i = 0
                    for answer in answers:
                        updated_answers[i] = {
                            "answer": answer,
                            "votes": 0
                        }
                        i += 1
                    data["questions"][current_index]["answers"] = updated_answers

                break
            current_index += 1
        if not found :
           if len(data["questions"]) == 0:
               current["id"] = 1
           else:
               next_id = data["questions"][-1]["id"]
               current["id"] = next_id + 1
           data["questions"].append(current)
           current_index = len(data["questions"])-1

    towrite = open('./plugins/survey/survey_questions.json', 'w')
    # TODO : make flexible

    json.dump(data, towrite, indent=4)
    towrite.close()

    #Compute the percentage for each answers
    i = 0
    nbVotesForEachAnswer = [None]*len(data["questions"][current_index]["answers"])
    for answer in data["questions"][current_index]["answers"]:
        nbVotesForEachAnswer[i] = answer["votes"]
        i += 1

    percent_votes = [None]*len(data["questions"][current_index]["answers"])
    totalNbVotes = data["questions"][current_index]["totalVotes"]
    if totalNbVotes != 0:
        i = 0
        for currentNbVotes in nbVotesForEachAnswer:
            percent_votes[i] = (currentNbVotes/totalNbVotes) * 100
            i += 1

    return [SurveyCapsule(question, author, answers, percent_votes, secret, channel_id, current["id"])]

def are_answers_updated(config_answers, saved_answers):
    #config_answers is a list of strings
    #saved_answers is a list of dictionary with a key "answer" and a key "votes"
    for saved_answer in saved_answers:
        if saved_answer["answer"] not in config_answers:
            return True
    return False

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
            if None in percent_votes:
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
