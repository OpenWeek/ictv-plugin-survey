# -*- coding: utf-8 -*-
#
#    This file was written by Arnaud Gellens, Arthur van Stratum,
#    Céline Deknop, Charles-Henry Bertrand Van Ouytsel,
#    Margerie Huet and Simon Gustin during the OpenWeek 2017 at
#    Universite Catholique de Louvain.
#    This software is licensed under the MIT License.


import json

import web
from ictv.models.channel import PluginChannel
from ictv.plugin_manager.plugin_capsule import PluginCapsule
from ictv.plugin_manager.plugin_manager import get_logger
from ictv.plugin_manager.plugin_slide import PluginSlide
from ictv.plugin_manager.plugin_utils import MisconfiguredParameters

from ictv.plugins.survey import questions_path


def get_content(channel_id):
    # Note : At the moment, question_id is always 1 (which allows only one question per channel)
    #       The idea would be to allow having several questions per channel using different IDs
    #       for each question in the JSON file.

    # From the configuration file
    channel = PluginChannel.get(channel_id)
    logger_extra = {'channel_name': channel.name, 'channel_id': channel.id}
    logger = get_logger('survey', channel)
    still_answerable = channel.get_config_param('answerable')
    question = channel.get_config_param('question')
    author = channel.get_config_param('author')
    answers = channel.get_config_param('answers')
    display_on_survey = channel.get_config_param('display_on_survey')

    if not question or not answers:
        logger.warning('Some of the required parameters are empty', extra=logger_extra)
        return []

    if len(answers) > 5:
        raise MisconfiguredParameters('answers', answers, "There shouldn't be more than 5 answers provided.")

    # For the .json
    current_question_entry = None
    must_write_json = False
    total_nb_votes = 0
    try:
        with open(questions_path, 'r') as data_file:
            saved_data = json.load(data_file)
    except:
        must_write_json = True
        saved_data = {
            str(channel_id): {
                '1': create_new_question_entry(question, answers)  # question_id = 1 (cf. note)
            }
        }

        ratio_votes = None
        current_question_entry = saved_data[str(channel_id)]['1']  # question_id = 1 (cf. note)
    else:
        # Check that the .json file is valid
        if not is_json_valid(saved_data):
            raise SyntaxError('The JSON file of the ICTV survey has an invalid syntax.')

        current_question_entry = find_question_entry(saved_data, channel_id)
        if current_question_entry is not None:
            # Check if the .json is up-to-date with the configuration
            if not is_json_up_to_date(current_question_entry, question, answers):
                must_write_json = True
                update_question(current_question_entry, question)
                if are_answers_updated(answers, current_question_entry['answers']):
                    update_answers(current_question_entry, answers)  # update and reset answers
            total_nb_votes = count_total_nb_votes(current_question_entry)
        else:  # the question was not contained in the .json file
            must_write_json = True
            new_question_entry = create_new_question_entry(question, answers)
            question_id = 1
            if len(saved_data[str(channel_id)]) != 0:
                question_id = get_greatest_question_id(saved_data[str(channel_id)]) + 1
            saved_data[str(channel_id)][str(question_id)] = new_question_entry
            current_question_entry = new_question_entry

        # Compute the percentage for each answers
        ratio_votes = compute_ratio_votes(current_question_entry['answers'], total_nb_votes)

    if must_write_json:
        with open(questions_path, 'w') as file_to_write:
            json.dump(saved_data, file_to_write, indent=4)

    return [SurveyCapsule(still_answerable, question, author, answers, ratio_votes, total_nb_votes, display_on_survey,
                          channel_id, 1)]  # question_id = 1 (cf. note)


def is_json_valid(json_data):
    """ Check if the .json file contains valid syntax for a survey """
    try:
        if json_data is None:
            return False
        for channel_key in json_data:
            if json_data[channel_key] is None:
                return False
            for question_key in json_data[channel_key]:
                if json_data[channel_key][question_key] is None:
                    return False
                if json_data[channel_key][question_key]['question'] is None:
                    return False
                if json_data[channel_key][question_key]['answers'] is None:
                    return False
                for answer in json_data[channel_key][question_key]['answers']:
                    if answer['answer'] is None:
                        return False
                    if answer['votes'] is None:
                        return False
        return True
    except (TypeError, KeyError):
        return False


def create_new_question_entry(question, answers):
    """ Creates a new entry for a question in the .json file (with id=1) and returns it """
    new_question_entry = {
        'question': question,
        'answers': []
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
    channel_entry = json_data.get(str(channel_id), None)
    if channel_entry is None:
        return None
    return channel_entry.get('1', None)


def is_json_up_to_date(current_question_entry, question, config_answers):
    """ Check if the .json file and the configuration are coherent with one another """
    if current_question_entry['question'] != question:
        return False
    if len(config_answers) != len(current_question_entry['answers']):
        return False
    elif are_answers_updated(config_answers, current_question_entry['answers']):
        return False
    return True


def are_answers_updated(config_answers, saved_answers):
    """ Check if all the saved answers are the answers stored in the configuration """
    # config_answers is a list of strings
    # saved_answers is a list of dictionary with a key "answer" and a key "votes"
    for saved_answer in saved_answers:
        if saved_answer["answer"] not in config_answers:
            return True
    return False


def update_question(current_question_entry, new_question):
    """
        Change the information contained in @current_question_entry to what's inside @new_question and @new_answers
        Reset the number of votes for each answer to the question
    """
    current_question_entry['question'] = new_question


def update_answers(current_question_entry, new_answers):
    """ Update and RESET the answers and the number of votes they have """
    updated_answers = []
    for answer in new_answers:
        updated_answers.append({
            "answer": answer,
            "votes": 0
        })
    current_question_entry["answers"] = updated_answers


def get_greatest_question_id(channel_entry):
    """ Return the greatest question id in @channel_entry as an integer """
    greatest_id = 0
    for question_key in channel_entry:
        question_id = int(float(question_key))
        if question_id > greatest_id:
            greatest_id = question_id
    return question_id


def count_total_nb_votes(current_question_entry):
    """ Count the total number of votes for all answers for the current question """
    total_nb_votes = 0
    for answer in current_question_entry['answers']:
        total_nb_votes += answer['votes']
    return total_nb_votes


def compute_ratio_votes(saved_answers, total_nb_votes):
    """ Compute the percentage of answer for each answer """
    if total_nb_votes == 0:
        return None

    ratio_votes = []
    for answer in saved_answers:
        ratio_votes.append(answer['votes'] / total_nb_votes)

    return ratio_votes


class SurveyCapsule(PluginCapsule):
    def __init__(self, still_answerable, question, author, answers, ratio_votes, total_nb_votes, display_on_survey,
                 channel_id, question_id):
        self._slides = [
            SurveySlide(still_answerable, question, author, answers, ratio_votes, total_nb_votes, display_on_survey,
                        channel_id, question_id)]

    def get_slides(self):
        return self._slides

    def get_theme(self):  # TODO : change that ?
        return None

    def __repr__(self):
        return str(self.__dict__)


class SurveySlide(PluginSlide):
    def __init__(self, still_answerable, question, author, answers, ratio_votes, total_nb_votes, display_on_survey,
                 channel_id, question_id):
        self._duration = 10000000
        self._content = {'still-answerable': still_answerable, 'title-1': {'text': question},
                         'text-0': {'text': author}}

        if len(answers) <= 5:
            self._content['nb-answers'] = len(answers)
        else:
            self._content['nb-answers'] = 5
        i = 1
        for answer in answers:
            self._content['text-' + str(i)] = {'text': answer}
            self._content['image-' + str(i)] = {
                'qrcode': web.ctx.homedomain + '/channels/' + str(channel_id) + '/validate/' + str(
                    question_id) + '/' + str(i)}
            i += 1

        self._content['total-nb-votes'] = total_nb_votes
        if display_on_survey:
            if ratio_votes is None:  # currently 0 votes
                self._content['show-results'] = False
                self._content['no-votes'] = True
            else:
                self._content['show-results'] = True
                self._content['no-votes'] = False
                self._content['ratio-votes'] = ratio_votes
        else:  # votes are not to be displayed on the survey screen
            self._content['show-results'] = False
            self._content['no-votes'] = None  # no information about this

    def get_duration(self):
        return self._duration

    def get_content(self):
        return self._content

    def get_template(self) -> str:
        return 'template-survey'

    def __repr__(self):
        return str(self.__dict__)
