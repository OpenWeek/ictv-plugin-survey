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

import errno
import web
import json
import traceback
import fcntl
import time
from ictv import get_root_path
from ictv.pages.utils import ICTVPage


def get_app(ictv_app):
    """ Returns the web.py application of the editor. """

    urls = (
        'index', 'ictv.plugins.survey.app.IndexPage',
        'validate/(.+)/(.+)', 'ictv.plugins.survey.app.Result',
        'stat/(.+)/(.+)', 'ictv.plugins.survey.app.Stat',
        'modify/(.+)', 'ictv.plugins.survey.app.Cancel'

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


class Result(SurveyPage):
    def GET(self, question, answer):
        questionTxt = "erreur: question inaccessible"
        answerTxt = "erreur: réponse inexistante"
        channel_id = -1
        try:
            data_file = open('./plugins/survey/survey_questions.json', 'r')
            data = json.load(data_file)
            data_file.close()
        except IOError:
            print("IOError !")
            traceback.print_exc()

        else:
            for e in data["questions"]:
                if str(e["id"]) == str(question):
                    questionTxt = e["question"]
                    channel_id = e["channel"]
                    i = 1
                    for el in e["answers"]:
                        if str(i) == answer:
                            answerTxt = el["answer"]
                        i += 1
        url_add = web.ctx.homedomain+'/channels/'+str(channel_id)+'/stat/'+question+'/'+answer
        url_cancel = web.ctx.homedomain + '/channels/' + str(channel_id) + '/modify/' + question
        return self.renderer.template_reponse(answer=answerTxt, question=questionTxt, url_add=url_add, url_cancel = url_cancel)  # + url stat


class IndexPage(SurveyPage):
    def GET(self):
        return "Hello World !"

class Stat(SurveyPage):
    def GET(self, id, answer):
        try:
            data_file = open('./plugins/survey/survey_questions.json', 'r')
            data = json.load(data_file)
            data_file.close()
            to_write = open('./plugins/survey/survey_questions.json', 'w')
        except IOError:
            print("IOError !")
            traceback.print_exc()
        else:
            for e in data["questions"]:
                if str(e["id"]) == str(id):
                    e["totalVotes"] += 1
                    i = 1
                    for el in e["answers"]:
                        if str(i) == answer:
                            el["votes"] += 1
                        i += 1
            json.dump(data, to_write, indent=4)
            to_write.close()
            for q in data["questions"]:
                if str(q["id"]) == id:
                    return self.renderer.template_stat(q)

            return "Not found"


class Cancel(SurveyPage):
    def GET(self, id):
            return "Test"
