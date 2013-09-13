#! /usr/bin/env python
# -*- coding: utf-8 -*-


# Etalab-CKAN-Scripts -- Various scripts that handle Etalab datasets in CKAN repository
# By: Emmanuel Raviart <emmanuel@raviart.com>
#
# Copyright (C) 2013 Emmanuel Raviart
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


"""Purge datasets already deleted in CKAN."""


import argparse
import logging
import os
import sys

from ckan import model, plugins
from ckan.config.environment import load_environment
from paste.deploy import appconfig
from paste.registry import Registry
import pylons
import sqlalchemy as sa
import sqlalchemy.exc
from sqlalchemy import sql


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

    bad_packages_name = []
    while True:
        revision = model.repo.new_revision()

        package = model.Session.query(model.Package).filter(
            model.Package.state == 'deleted',
            sa.not_(model.Package.name.in_(bad_packages_name)) if bad_packages_name else None,
            ).first()
        if package is None:
            break

        name = package.name
        title = package.title

        # Delete resource_revision before purging package, to avoid IntegrityError: update or delete on table
        # "resource_group" violates foreign key constraint "resource_revision_resource_group_id_fkey" on table
        # "resource_revision".
        for resource_group in model.Session.query(model.ResourceGroup).filter(
                model.ResourceGroup.package_id == package.id,
                ):
            for resource_revision in model.Session.query(model.ResourceRevision).filter(
                    model.ResourceRevision.resource_group_id == resource_group.id,
                    ):
                model.Session.delete(resource_revision)

        package.purge()
        log.info(u'Purged package {} - {}'.format(name, title))

        try:
            model.repo.commit_and_remove()
        except sqlalchemy.exc.IntegrityError:
            log.exception(u'An integrity error while purging {} - {}'.format(name, title))
            bad_packages_name.append(name)

    return 0


if __name__ == '__main__':
    sys.exit(main())