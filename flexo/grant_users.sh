#!/usr/bin/env bash
# Give every LDAP user listed in .env the Flexo super-admin role (safe to run again).
set -euo pipefail
cd "$(dirname "$0")"
source <(grep -E '^LDAP_USERS=' .env)
subjects=""; agents=""
for u in ${LDAP_USERS//,/ }; do
  for iri in "http://layer1-service/users/ldap/user/$u" "http://layer1-service/users/$u"; do
    subjects+="<$iri>, "
    agents+="<$iri> a mms:User ; mms:id \"${iri#http://layer1-service/users/}\" . "
  done
done
subjects=${subjects%, }
curl -sf -o /dev/null -w "update HTTP %{http_code}\n" http://127.0.0.1:3030/ds/update --data-urlencode "update=
PREFIX mms: <https://mms.openmbee.org/rdf/ontology/>
PREFIX mms-object: <https://mms.openmbee.org/rdf/objects/>
INSERT DATA {
  GRAPH <http://layer1-service/graphs/AccessControl.Agents> { $agents }
  GRAPH <http://layer1-service/graphs/AccessControl.Policies> {
    <http://layer1-service/policies/PipelineUsersSuperAdmins> a mms:Policy ;
      mms:subject $subjects ;
      mms:scope <http://layer1-service/> ;
      mms:role mms-object:Role.AdminCluster, mms-object:Role.AdminOrg, mms-object:Role.AdminRepo,
               mms-object:Role.AdminMetadata, mms-object:Role.AdminModel, mms-object:Role.AdminAccessControlAny .
  }
}"
echo "granted admin to: $LDAP_USERS"
