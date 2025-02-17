#
# Copyright (C) 2022 by frePPLe bv
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os.path
import psycopg2
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS

from freppledb import __version__
from freppledb.common.models import Parameter


class Command(BaseCommand):

    help = "Utility command for development to spin up an odoo docker container"

    requires_system_checks = []

    def get_version(self):
        return __version__

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            dest="full",
            default=False,
            help="Complete rebuild of image and database",
        )
        parser.add_argument(
            "--nolog",
            action="store_true",
            dest="nolog",
            default=False,
            help="Tail the odoo log at the end of this command",
        )
        parser.add_argument(
            "--container-port",
            type=int,
            default=8069,
            help="Port number for odoo. Defaults to 8069",
        )
        parser.add_argument(
            "--frepple-url",
            default="http://localhost:8000",
            help="URL where frepple is available. Defaults to 'http://localhost:8000'",
        )
        parser.add_argument(
            "--odoo-url",
            default="http://localhost:8069",
            help="URL where odoo is available. Defaults to 'http://localhost:8069'",
        )
        parser.add_argument(
            "--odoo-db-host",
            default=settings.DATABASES[DEFAULT_DB_ALIAS]["HOST"],
            help="Database host to use for odoo. Defaults to the same as used by frepple.",
        )
        parser.add_argument(
            "--odoo-db-port",
            default=settings.DATABASES[DEFAULT_DB_ALIAS]["PORT"],
            help="Database port to use for odoo. Defaults to the same as used by frepple.",
        )
        parser.add_argument(
            "--odoo-db-user",
            default=settings.DATABASES[DEFAULT_DB_ALIAS]["USER"],
            help="Database user to use for odoo. Defaults to the same as used by frepple.",
        )
        parser.add_argument(
            "--odoo-db-password",
            default=settings.DATABASES[DEFAULT_DB_ALIAS]["PASSWORD"],
            help="Database password to use for odoo. Defaults to the same as used by frepple.",
        )
        parser.add_argument(
            "--odoo-addon-path",
            default=os.path.join(os.path.dirname(__file__), "..", "..", "odoo_addon"),
            help="Location of the odoo connectors to install.",
        )

    def getOdooVersion(self, dockerfile):
        with open(dockerfile, mode="rt") as f:
            for l in f.read().splitlines():
                if l.startswith("FROM "):
                    return l.split(":", 1)[-1]
            raise CommandError("Can't find odoo version in dockerfile")

    def handle(self, **options):
        dockerfile = os.path.join(options["odoo_addon_path"], "dockerfile")
        if not os.path.exists(dockerfile):
            raise CommandError("Can't find dockerfile")
        odooversion = self.getOdooVersion(dockerfile)

        # Used as a) docker image name, b) docker container name,
        # c) docker volume name and d) odoo database name.
        name = "odoo_frepple_%s" % odooversion

        if options["full"]:
            print("PULLING ODOO BASE IMAGE")
            subprocess.run(["docker", "pull", "odoo:%s" % odooversion])

        print("BUILDING DOCKER IMAGE")
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                dockerfile,
                "-t",
                name,
                ".",
            ],
            cwd=options["odoo_addon_path"],
        )

        print("DELETE OLD CONTAINER")
        subprocess.run(["docker", "rm", "--force", name])
        if options["full"]:
            subprocess.run(["docker", "volume", "rm", "--force", name])

        if options["full"]:
            print("CREATE NEW DATABASE")
            os.environ["PGPASSWORD"] = options["odoo_db_password"]
            extraargs = []
            if options["odoo_db_host"]:
                extraargs = extraargs + [
                    "-h",
                    options["odoo_db_host"],
                ]
            if options["odoo_db_port"]:
                extraargs = extraargs + [
                    "-p",
                    options["odoo_db_port"],
                ]
            subprocess.run(
                [
                    "dropdb",
                    "-U",
                    options["odoo_db_user"],
                    "--force",
                    "--if-exists",
                    name,
                ]
                + extraargs
            )
            subprocess.run(
                [
                    "createdb",
                    "-U",
                    options["odoo_db_user"],
                    name,
                ]
                + extraargs
            )

            print("INITIALIZE ODOO DATABASE")
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    "%s:/var/lib/odoo" % name,
                    "-e",
                    "HOST=%s"
                    % (
                        "host.docker.internal"
                        if not options["odoo_db_host"]
                        else options["odoo_db_host"]
                    ),
                    "-e",
                    "USER=%s" % options["odoo_db_user"],
                    "-e",
                    "PASSWORD=%s" % options["odoo_db_password"],
                    "--name",
                    name,
                    name,
                    "odoo",
                    "--init=base,product,purchase,sale,sale_management,resource,stock,mrp,frepple,freppledata,autologin",
                    "--load=web,autologin",
                    "--database=%s" % name,
                    "--stop-after-init",
                ]
            )

            print("CONFIGURE ODOO DATABASE")
            conn_params = {
                "database": name,
                "user": options["odoo_db_user"],
                "password": options["odoo_db_password"],
            }
            if options["odoo_db_host"]:
                conn_params["host"] = options["odoo_db_host"]
            if options["odoo_db_port"]:
                conn_params["port"] = options["odoo_db_port"]
            with psycopg2.connect(**conn_params) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        update res_company set
                          manufacturing_warehouse = (
                             select id
                             from stock_warehouse
                             where stock_warehouse.company_id = res_company.id
                             order by id
                             limit 1
                             ),
                          webtoken_key = '%s',
                          frepple_server = '%s',
                          disclose_stack_trace = true
                        """
                        % (
                            settings.DATABASES[DEFAULT_DB_ALIAS].get(
                                "SECRET_WEBTOKEN_KEY", None
                            )
                            or settings.SECRET_KEY,
                            options["frepple_url"],
                        )
                    )
                    cursor.execute(
                        """
                        select res_company.name, stock_warehouse.name
                        from res_company
                        inner join res_users
                          on res_users.company_id = res_company.id
                          and login = 'admin'
                        inner join stock_warehouse
                          on stock_warehouse.company_id = res_company.id
                        order by stock_warehouse.id
                        """
                    )
                    company, mfglocation = cursor.fetchone()

            print("CONFIGURE FREPPLE PARAMETERS")
            Parameter.objects.all().filter(name="odoo.company").update(value=company)
            Parameter.objects.all().filter(name="odoo.db").update(value=name)
            Parameter.objects.all().filter(name="odoo.user").update(value="admin")
            Parameter.objects.all().filter(name="odoo.password").update(value="admin")
            Parameter.objects.all().filter(name="odoo.production_location").update(
                value=mfglocation
            )
            Parameter.objects.all().filter(name="odoo.url").update(
                value=options["odoo_url"]
            )

        print("CREATING DOCKER CONTAINER")
        container = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "-p",
                "%s:8069" % (options["container_port"],),
                "-p",
                "%s:8071" % (options["container_port"] + 2,),
                "-p",
                "%s:8072" % (options["container_port"] + 3,),
                "-v",
                "%s:/var/lib/odoo" % name,
                "-e",
                "HOST=%s"
                % (
                    "host.docker.internal"
                    if not options["odoo_db_host"]
                    else options["odoo_db_host"]
                ),
                "-e",
                "USER=%s" % options["odoo_db_user"],
                "-e",
                "PASSWORD=%s" % options["odoo_db_password"],
                "--name",
                name,
                "-t",
                name,
                "odoo",
                "--database=%s" % name,
            ],
            capture_output=True,
            text=True,
        ).stdout

        print("CONTAINER READY: %s " % container)
        if not options["nolog"]:
            print("Hit CTRL-C to stop displaying the container log")
            subprocess.run(["docker", "attach", container], shell=True)
