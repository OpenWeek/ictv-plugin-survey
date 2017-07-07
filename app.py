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
import re

#pour generer le csv:
import io
import csv

import errno
import web
import json
import traceback
import fcntl
import time
from ictv import get_root_path
from ictv.pages.utils import ICTVPage
from ictv.plugin_manager.plugin_utils import ChannelGate


def get_app(ictv_app):
    """ Returns the web.py application of the editor. """

    urls = (
        'index', 'ictv.plugins.survey.app.IndexPage',
        'index/(.+)', 'ictv.plugins.survey.app.IndexPage',
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
    @ChannelGate.contributor
    def GET(self, download=None, channel=None):
        c_tmp = re.findall(r'\d+', web.ctx.homepath)
        c = str(c_tmp[0])
        if download:
            try:
                data_file = open('./plugins/survey/survey_questions.json', 'r')
                data = json.load(data_file)
                data_file.close()

            except IOError:
                print("IOError !")
                traceback.print_exc()

            else:
                chan_data = data[c]
                output = io.StringIO()
                csv_output = csv.writer(output)
                csv_output.writerow(["ID_Question", "Question", "Answer_1", "Votes_1", "Answer_2", "Votes_2","Answer_3", "Votes_3", "Answer_4", "Votes_4","Answer_5", "Votes_5"])
                for q in chan_data:
                    csv_data = []
                    csv_data.append(q)
                    csv_data.append(str(chan_data[q]["question"]))
                    for i in range(0,5):
                        if i < len(chan_data[q]["answers"]):
                            csv_data.append(chan_data[q]["answers"][i]["answer"])
                            csv_data.append(chan_data[q]["answers"][i]["votes"])
                        else:
                            csv_data.append("\\")
                            csv_data.append("NA")
                    csv_output.writerow(csv_data)
                return output.getvalue()
                #return "Hello World !"
        else:
            name_files = "result_channel_"+c+".csv"
            #return "<a href="+web.ctx.homedomain+web.ctx.homepath+"index/"+name_files+">download</a>"
            return self.renderer.template_download(url=web.ctx.homedomain+web.ctx.homepath+"index/"+name_files)

class Stat(SurveyPage):
    def GET(self, id, answer=None):
        if answer != None:
            web.redirect(str(web.ctx.homedomain)+str(web.ctx.homepath) + "stat/" + str(id))
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
                    hash = hashlib.md5(("un peu de texte non previsible" + str(e["channel"]) + str(id)).encode('utf-8')).hexdigest()
                    #print("cookies: "+str(web.cookies().get('webpy_session_id')))
                    if not web.cookies().get(hash):
                        i = 1
                        for el in e["answers"]:
                            if str(i) == answer:
                                el["votes"] += 1
                                #set cookies
                                web.setcookie(hash,1, path=web.ctx.homepath)
                                break
                            i += 1
                    else:
                        print("cookie recognized")
            json.dump(data, to_write, indent=4)
            to_write.close()
            for q in data["questions"]:
                if str(q["id"]) == id:
                    return self.renderer.template_stat(q)

            return "Not found"


class Modify(SurveyPage):
    def GET(self, id):
        answers = []
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
                if str(e["id"]) == str(id):
                    questionTxt = e["question"]
                    channel_id = e["channel"]
                    for el in e["answers"]:
                        answers.append(el["answer"])
        url = web.ctx.homedomain + '/channels/' + str(channel_id) + '/validate/' + id + '/'
        return self.renderer.template_modify(answers=answers, question=questionTxt, url=url)
