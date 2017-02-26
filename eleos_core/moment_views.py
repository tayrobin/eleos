import json
import psycopg2
from django.http import HttpResponse


def createNewMoment(request):

    if request.method == "POST":
        print "POST:", request
        print "POST request:", request.POST
        data = json.loads(request.POST)
        print "Data:", data
    else:
        print "Not a POST"
        print request

    return HttpResponse('OK')
