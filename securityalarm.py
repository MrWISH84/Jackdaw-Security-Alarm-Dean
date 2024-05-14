##
 # Jackdaw Security Alarm
 # Copyright (C) 2024 St Edmund's College at the University of Cambridge
 # 
 # Jackdaw Security Alarm is free software: you can redistribute it and/or modify
 # it under the terms of the GNU Affero General Public License as published by
 # the Free Software Foundation, version 3 of the License.
 # 
 # Jackdaw Security Alarm is distributed in the hope that it will be useful,
 # but WITHOUT ANY WARRANTY; without even the implied warranty of
 # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 # GNU General Public License for more details.
 # 
 # You should have received a copy of the GNU General Public License
 # along with Spin Doctor.  If not, see <https://www.gnu.org/licenses/>.
##

from ibisclient import createTestConnection, InstitutionMethods

connection = createTestConnection()

methods = InstitutionMethods(connection)

people = methods.getMembers("EDMUND")
for person in people:
    print("  - %s: %s" % (person.identifier.value, person.visibleName))
