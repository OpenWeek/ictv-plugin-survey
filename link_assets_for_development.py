#!/usr/bin/env python3
import sys
import os

try:
    import ictv.renderer
    renderer_path = ictv.renderer.__path__[0]
except (TypeError, ImportError):
    print('ICTV core could not be found, aborting')
    sys.exit(-1)

remove = len(sys.argv) > 1

parent_dir = os.path.dirname(os.path.abspath(__file__))
themes_dir = os.path.join(parent_dir, 'ictv', 'renderer', 'themes')
templates_dir = os.path.join(parent_dir, 'ictv', 'renderer', 'templates')

if os.path.exists(themes_dir):
    for theme in os.listdir(themes_dir):
        link = os.path.join(renderer_path, 'themes', theme)
        if not remove and not os.path.exists(link):
            os.symlink(os.path.join(themes_dir, theme), link, target_is_directory=True)
            print('Installed theme ' + theme)
        elif remove and os.path.exists(link):
            os.unlink(link)
            print('Removed theme ' + theme)

if os.path.exists(templates_dir):
    for template in os.listdir(templates_dir):
        link = os.path.join(renderer_path, 'templates', template)
        if not remove and not os.path.exists(link):
            os.symlink(os.path.join(templates_dir, template), link)
            print('Installed template ' + template)
        elif remove and os.path.exists(link):
            os.unlink(link)
            print('Removed template ' + template)
