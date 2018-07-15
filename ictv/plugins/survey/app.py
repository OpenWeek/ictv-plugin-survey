# -*- coding: utf-8 -*-
#
#    This file was written by Arnaud Gellens, Arthur van Stratum,
#    Céline Deknop, Charles-Henry Bertrand Van Ouytsel,
#    Margerie Huet and Simon Gustin during the OpenWeek 2017 at
#    Universite Catholique de Louvain.
#    This software is licensed under the MIT License.


import csv
import hashlib
# pour generer le csv:
import io
import json
import os
import re
import traceback

import web

from ictv.models.channel import PluginChannel
from ictv.pages.utils import ICTVPage
from ictv.plugin_manager.plugin_manager import get_logger
from ictv.plugin_manager.plugin_utils import ChannelGate, seeother
from ictv.plugins.survey import questions_path


def get_app(ictv_app):
    """ Returns the web.py application of the editor. """

    urls = (
        'index', 'ictv.plugins.survey.app.IndexPage',
        'index/(.+)', 'ictv.plugins.survey.app.IndexPage',
        'confirm/(.+)/(.+)', 'ictv.plugins.survey.app.Confirm',
        'stat/(.+)', 'ictv.plugins.survey.app.Stat',
        'modify/(.+)', 'ictv.plugins.survey.app.Modify'

    )

    app = web.application(urls, globals())
    app.renderer = web.template.render(os.path.join(os.path.dirname(__file__), 'templates'),
                                       globals={'print': print, 'str': str})

    SurveyPage.plugin_app = app

    return app


class SurveyPage(ICTVPage):
    plugin_app = None
    logger = get_logger('survey')

    @property
    def survey_app(self):
        """ Returns the web.py application singleton of the editor. """
        return SurveyPage.plugin_app

    @property
    def renderer(self):
        """ Returns the webapp renderer. """
        return self.survey_app.renderer

    @property
    def plugin_logger(self):
        """ Returns the plugin logger. """
        return SurveyPage.logger


class Confirm(SurveyPage):
    def GET(self, question_id, answer_id):
        try:
            with open(questions_path, 'r') as data_file:
                data = json.load(data_file)
        except IOError:
            self.logger.warn('An exception occurred when opening the questions file', exc_info=True)
            return web.seeother('/')

        channel_id = get_channel_id_from_url(web.ctx.homepath)
        question_entry = get_question_entry(data, channel_id, question_id)
        question_txt = question_entry['question']
        answer_txt = question_entry['answers'][int(answer_id)]['answer'] \
            if 0 <= int(answer_id) <= len(question_entry['answers']) else None

        url_add = web.ctx.homedomain + '/channels/' + str(channel_id) + '/confirm/' + question_id + '/' + answer_id
        url_cancel = web.ctx.homedomain + '/channels/' + str(channel_id) + '/modify/' + question_id

        if not question_txt or not answer_txt:
            self.logger.warn("The survey question or the answer to the question couldn't be found in the JSON file.")
            seeother(channel_id, '/modify/' + question_id)

        return self.renderer.template_reponse(answer=answer_txt, question=question_txt, url_add=url_add,
                                              url_cancel=url_cancel)  # + url stat

    def POST(self, question_id, answer_id):
        with open(questions_path, 'r') as data_file:
            data = json.load(data_file)

        channel_id = get_channel_id_from_url(web.ctx.homepath)
        channel = PluginChannel.get(channel_id)
        question_entry = get_question_entry(data, channel_id, question_id)

        if question_entry:
            vote_hash = hashlib.md5((str(channel_id) + question_id + question_entry['question']).encode('utf-8')).hexdigest()
            if not web.cookies().get(vote_hash) and 0 <= int(answer_id) <= len(question_entry["answers"]):
                question_entry['answers'][int(answer_id)]['votes'] += 1
                web.setcookie(vote_hash, 1, path=web.ctx.homepath)
                with open(questions_path, 'w') as to_write:
                    json.dump(data, to_write)

                if channel.get_config_param('display_in_webapp'):
                    raise seeother(channel_id, '/stat/' + question_id)
                return self.renderer.template_merci()
            elif not channel.get_config_param('display_in_webapp'):
                return self.renderer.template_merci(already_voted=True)

        raise seeother(channel_id, '/stat/' + question_id)


class IndexPage(SurveyPage):
    @ChannelGate.contributor
    def GET(self, download=None, channel=None):
        c_tmp = re.findall(r'\d+', web.ctx.homepath)
        c = str(c_tmp[0])
        if download:
            try:
                data_file = open(questions_path, 'r')
                data = json.load(data_file)
                data_file.close()

            except IOError:
                print("IOError !")
                traceback.print_exc()

            else:
                chan_data = data[c]
                output = io.StringIO()
                csv_output = csv.writer(output)
                csv_output.writerow(
                    ["ID_Question", "Question", "Answer_1", "Votes_1", "Answer_2", "Votes_2", "Answer_3", "Votes_3",
                     "Answer_4", "Votes_4", "Answer_5", "Votes_5"])
                for q in chan_data:
                    csv_data = [q, str(chan_data[q]["question"])]
                    for i in range(0, 5):
                        if i < len(chan_data[q]["answers"]):
                            csv_data.append(chan_data[q]["answers"][i]["answer"])
                            csv_data.append(chan_data[q]["answers"][i]["votes"])
                        else:
                            csv_data.append("\\")
                            csv_data.append("NA")
                    csv_output.writerow(csv_data)
                return output.getvalue()
                # return "Hello World !"
        else:
            name_files = "result_channel_" + c + ".csv"
            # return "<a href="+web.ctx.homedomain+web.ctx.homepath+"index/"+name_files+">download</a>"
            return self.renderer.template_download(url=web.ctx.homedomain + web.ctx.homepath + "index/" + name_files)


class Stat(SurveyPage):
    def GET(self, question_id, answer=None):
        channel_id = get_channel_id_from_url(web.ctx.homepath)

        if answer is not None:
            raise seeother(channel_id, '/stat/' + question_id)

        with open(questions_path, 'r') as data_file:
            data = json.load(data_file)

        question_entry = get_question_entry(data, channel_id, question_id)
        if question_entry and PluginChannel.get(channel_id).get_config_param('display_in_webapp'):
            return self.renderer.template_stat(question_entry)
        raise web.forbidden()


class Modify(SurveyPage):
    def GET(self, question_id):
        answers = []
        channel_id = get_channel_id_from_url(web.ctx.homepath)
        try:
            with open(questions_path, 'r') as data_file:
                data = json.load(data_file)
        except IOError:
            print("IOError !")
            traceback.print_exc()
        else:
            question_entry = get_question_entry(data, channel_id, question_id)
            if question_entry is not None:
                question_txt = question_entry['question']
                for current_answer in question_entry['answers']:
                    answers.append(current_answer["answer"])
            else:
                raise KeyError("The question with this ID(%s) is not contained in the JSON file." % question_id)

        url = web.ctx.homedomain + '/channels/' + str(channel_id) + '/confirm/' + question_id + '/'
        return self.renderer.template_modify(answers=answers, question=question_txt, url=url)


def get_channel_id_from_url(url):
    return re.findall(r'\d+', url)[0]


def get_question_entry(json_data, channel_id, question_id):
    channel_entry = json_data.get(str(channel_id), None)
    if channel_entry is None:
        return None
    return channel_entry.get(str(question_id), None)
