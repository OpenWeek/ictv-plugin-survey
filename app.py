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


import os
import hashlib

import errno
import web
import json
import traceback
import fcntl
import time
from ictv import get_root_path
from ictv.pages.utils import ICTVPage
import re


def get_app(ictv_app):
    """ Returns the web.py application of the editor. """

    urls = (
        'index', 'ictv.plugins.survey.app.IndexPage',
        'validate/(.+)/(.+)', 'ictv.plugins.survey.app.Validate',
        'stat/(.+)/(.+)', 'ictv.plugins.survey.app.Stat',
        'stat/(.+)', 'ictv.plugins.survey.app.Stat',
        'modify/(.+)', 'ictv.plugins.survey.app.Modify'

    )

    app = web.application(urls, globals())
    app.renderer = web.template.render(os.path.join(get_root_path(), 'plugins/survey/templates'), globals={'print':print, 'str':str})

    SurveyPage.plugin_app = app

    return app


class SurveyPage(ICTVPage):
    plugin_app = None

    @property
    def survey_app(self):
        """ Returns the web.py application singleton of the editor. """
        return SurveyPage.plugin_app

    @property
    def renderer(self):
        """ Returns the webapp renderer. """
        return self.survey_app.renderer


class Validate(SurveyPage):
    def GET(self, question_id, answer):
        question_txt = None
        answer_txt = None
        channel_id = -1
        try:
            with open('./plugins/survey/survey_questions.json', 'r') as data_file:
                data = json.load(data_file)
        except IOError:
            print("IOError !")
            traceback.print_exc()
        else:
            channel_id = get_channel_id_from_url(web.ctx.homepath)
            question_entry = get_question_entry(data, channel_id, question_id)
            question_txt = question_entry['question']
            i = 1
            for current_answer in question_entry['answers']:
                if str(i) == answer:
                    answer_txt = current_answer['answer']
                i += 1

        url_add = web.ctx.homedomain+'/channels/'+str(channel_id)+'/stat/'+question_id+'/'+answer
        url_cancel = web.ctx.homedomain + '/channels/' + str(channel_id) + '/modify/' + question_id

        if question_txt == None or answer_txt == None:
            raise KeyError("The survey question or the answers to the question couldn't be found in the JSON file.")

        return self.renderer.template_reponse(answer=answer_txt, question=question_txt, url_add=url_add, url_cancel = url_cancel)  # + url stat

class IndexPage(SurveyPage):
    def GET(self):
        return "Hello World !"

class Stat(SurveyPage):
    def GET(self, question_id, answer=None):
        if answer != None:
            web.redirect(str(web.ctx.homedomain)+str(web.ctx.homepath) + "stat/" + str(question_id))
        try:
            with open('./plugins/survey/survey_questions.json', 'r') as data_file:
                data = json.load(data_file)
        except IOError:
            print("IOError !")
            traceback.print_exc()
        else:
            channel_id = get_channel_id_from_url(web.ctx.homepath)
            question_entry = get_question_entry(data, channel_id, question_id)

            if question_entry != None:
                hash = hashlib.md5(("un peu de texte non previsible" + str(channel_id) + str(question_id)).encode('utf-8')).hexdigest()
                #print("cookies: "+str(web.cookies().get('webpy_session_id')))
                if not web.cookies().get(hash):
                    i = 1
                    for current_answer in question_entry["answers"]:
                        if str(i) == answer:
                            current_answer["votes"] += 1
                            #set cookies
                            web.setcookie(hash,1, path=web.ctx.homepath)
                            break
                        i += 1
                else:
                    print("cookie recognized")

                with open('./plugins/survey/survey_questions.json', 'w') as to_write:
                    json.dump(data, to_write, indent=4)

                return self.renderer.template_stat(question_entry)
            else:
                return "Not found"

class Modify(SurveyPage):
    def GET(self, question_id):
        answers = []
        channel_id = get_channel_id_from_url(web.ctx.homepath)
        try:
            with open('./plugins/survey/survey_questions.json', 'r') as data_file:
                data = json.load(data_file)
        except IOError:
            print("IOError !")
            traceback.print_exc()
        else:
            question_entry = get_question_entry(data, channel_id, question_id)
            if question_entry != None:
                question_txt = question_entry['question']
                for current_answer in question_entry['answers']:
                    answers.append(current_answer["answer"])
            else:
                raise KeyError("The question with this ID(%d) is not contained in the JSON file." % quesion_id)

        url = web.ctx.homedomain + '/channels/' + str(channel_id) + '/validate/' + question_id + '/'
        return self.renderer.template_modify(answers=answers, question=question_txt, url=url)

def get_channel_id_from_url(url):
    return re.findall(r'\d+', url)[0]

def get_question_entry(json_data, channel_id, question_id):
    channel_entry = json_data.get(str(channel_id), None)
    if channel_entry == None:
        return None
    return channel_entry.get(str(question_id), None)
