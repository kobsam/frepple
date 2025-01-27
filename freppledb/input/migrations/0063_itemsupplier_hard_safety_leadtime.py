# Copyright (C) 2022 by frePPLe bv
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

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("input", "0062_parameter_fix_supply_path"),
    ]

    operations = [
        migrations.AddField(
            model_name="itemsupplier",
            name="hard_safety_leadtime",
            field=models.DurationField(
                blank=True,
                help_text="hard safety lead time",
                null=True,
                verbose_name="hard safety lead time",
            ),
        ),
    ]
