import json
import psycopg2
import psycopg2.extras
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
            "trigger": request.POST.get("trigger"),
            "content": request.POST.get("content"),
            "lat": request.POST.get("lat"),
            "lng": request.POST.get("lng"),
            "radius": request.POST.get("radius")
        }

        for key in data:
            if data.get(key) and type(data.get(key)) == list:
                data[key] = data[key][0]

        try:
            data["content"] = psycopg2.extras.Json(json.loads(data.get("content")))
        except:
            print "Invalid JSON for Content:", data.get("content")
            return HttpResponse("Invalid JSON for Content")

        print "Insert Data to Eleos database:", data

        conn = psycopg2.connect(
            "postgres://root:BbpVbwuGGjhKaEzf3xJi@eleos-development.crimoo44c8hn.us-east-1.rds.amazonaws.com/eleos_development")
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        insertStatement = "INSERT INTO moments (trigger, content, latlng, radius) VALUES (%(trigger)s, %(content)s, ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)::geography, %(radius)s)"

        cur.execute(insertStatement, data})
        conn.commit()

        print "Inserted successfully!"

    return HttpResponse('OK')
