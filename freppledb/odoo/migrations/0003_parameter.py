#
# Copyright (C) 2020 by frePPLe bv
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("odoo", "0002_parameters")]

    operations = [
        migrations.RunSQL(
            """
            insert into common_parameter
            (name, value, description, lastmodified)
            values
            ('odoo.loglevel','0','Odoo connector: Set to non-zero to get a verbose log. Default is 0.', now())
            on conflict(name) do nothing
            """
        )
    ]
