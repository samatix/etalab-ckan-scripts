#! /usr/bin/env python
# -*- coding: utf-8 -*-


# Etalab-CKAN-Scripts -- Various scripts that handle Etalab datasets in CKAN repository
# By: Emmanuel Raviart <emmanuel@raviart.com>
#
# Copyright (C) 2013 Etalab
# http://github.com/etalab/etalab-ckan-scripts
#
# This file is part of Etalab-CKAN-Scripts.
#
# Etalab-CKAN-Scripts is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Etalab-CKAN-Scripts is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""Repair territorial_coverage_granularity extra fields."""


import argparse
import json
import logging
import os
import sys
import urllib
import urllib2
import urlparse

from ckan import model, plugins
from ckan.config.environment import load_environment
from paste.deploy import appconfig
from paste.registry import Registry
import pylons


app_name = os.path.splitext(os.path.basename(__file__))[0]
log = logging.getLogger(app_name)


class MockTranslator(object):
    def gettext(self, value):
        return value

    def ugettext(self, value):
        return value

    def ungettext(self, singular, plural, n):
        if n > 1:
            return plural
        return singular


def main():
    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument('config', help = 'path of configuration file')
    parser.add_argument('-t', '--territoria-url', help = 'Territoria URL', required = True)
    parser.add_argument('-v', '--verbose', action = 'store_true', help = 'increase output verbosity')

    args = parser.parse_args()
#    logging.basicConfig(level = logging.DEBUG if args.verbose else logging.WARNING, stream = sys.stdout)
    logging.basicConfig(level = logging.INFO if args.verbose else logging.WARNING, stream = sys.stdout)
    site_conf = appconfig('config:{}'.format(os.path.abspath(args.config)))
    load_environment(site_conf.global_conf, site_conf.local_conf)

    registry = Registry()
    registry.prepare()
    registry.register(pylons.translator, MockTranslator())

    plugins.load('synchronous_search')

    model.repo.new_revision()

    kind_code_name_by_kind_code = {}
    for package_extra in model.Session.query(model.PackageExtra).filter(
            model.PackageExtra.key == 'territorial_coverage_granularity',
            model.PackageExtra.value == 'france',
            ):
        package = package_extra.package
        if package.private or package.state != 'active':
            log.warning(u'Territorial coverage granularity of package {} must be manually corrected'.format(
                package.name))
            continue
        package_extra.value = 'pays'

    model.repo.commit_and_remove()

    return 0


if __name__ == '__main__':
    sys.exit(main())
