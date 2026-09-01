with open("terraform/dashboard.tf", "r") as f:
    content = f.read()

content = content.replace('"EdgeRequests"', '"Edge_requests"')
content = content.replace('"EdgeHitRequests"', '"Edge_hit_requests"')
content = content.replace('"EdgeMissRequests"', '"Edge_miss_requests"')
content = content.replace('"ShieldFetches"', '"Shield_fetches"')
content = content.replace('"ShieldHitRequests"', '"Shield_hit_requests"')
content = content.replace('"DdosProtectionRequestsDetectCount"', '"Ddos_protection_requests_detect_count"')
content = content.replace('"DdosProtectionRequestsMitigateCount"', '"Ddos_protection_requests_mitigate_count"')

with open("terraform/dashboard.tf", "w") as f:
    f.write(content)
