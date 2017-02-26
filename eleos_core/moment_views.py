import psycopg2


def createNewMoment(request):

    if request.method == "POST":
        print request
    else:
        print "Not a POST"
        print request
