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


import copy
import ipaddress
import json
import os
from collections import OrderedDict
import web
from ictv.pages.utils import ICTVPage


def get_app(ictv_app):
    """ Returns the web.py application of the editor. """

    urls = (
        'index', 'IndexPage',
        'result', 'ictv.plugins.survey.app.ResultPage'
    )

    app = web.application(urls, globals())
    #app.renderer = web.template.render(globals={})

    SurveyPage.plugin_app = app

    return app


class SurveyPage(ICTVPage):
    plugin_app = None

    @property
    def editor_app(self):
        """ Returns the web.py application singleton of the editor. """
        return SurveyPage.plugin_app

    @property
    def renderer(self):
        """ Returns the webapp renderer. """
        return self.editor_app.renderer


class ResultPage(SurveyPage):
    def GET(self):
        return "Test"


class IndexPage(SurveyPage):
    def GET(self):
        return "Hello World !"