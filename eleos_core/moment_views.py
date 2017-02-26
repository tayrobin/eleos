import json
import psycopg2, psycopg2.extras
from django.http import HttpResponse


def createNewMoment(request):

    if not request.method == "POST":
        print "Not a POST"
        print request
        return HttpResponse("Not a POST request.")
    else:
        print "POST:", request
        print "POST request:", request.POST

        data = {
            "trigger" = request.POST.get("trigger")[0]
            "content" = request.POST.get("content")[0]
            "lat" = request.POST.get("lat")
            "lng" = request.POST.get("lng")
            "radius" = request.POST.get("radius")
        }

        for key in data:
            if key and type(key) == list:
                data[key] = data[key][0]

        try:
            data["content"] = json.loads(data.get("content"))
        except:
            print "Invalid JSON:", data.get("content")
            return HttpResponse("Invalid JSON for Content")

        print "Insert Data to Eleos database:", data

        conn = psycopg2.connect("postgres://root:BbpVbwuGGjhKaEzf3xJi@eleos-development.crimoo44c8hn.us-east-1.rds.amazonaws.com/eleos_development")
		cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    return HttpResponse('OK')
