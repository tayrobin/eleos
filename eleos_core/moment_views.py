import psycopg2
from django.http import HttpResponse


def createNewMoment(request):

    if request.method == "POST":
        print request
    else:
        print "Not a POST"
        print request

    return HttpResponse('OK')
