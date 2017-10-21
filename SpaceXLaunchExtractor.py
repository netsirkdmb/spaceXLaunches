# pylint: disable=W

"""
Notes:
- Does not handle launch windows.  Event always starts and ends at the start of the window
- When launchtime is TBD, creates all-day event
- If date is undetermined, adds launch to error list
- If date is determined, adds launch to calendar and increments year to next year correctly
  assuming the launches are listed in chronological order, need to examine what happens
  in December and January
- Does not search calendar events to make sure events aren't duplicated.  Need to search
  events and if there is already a matching event summary, replace or update the event
"""

"""This script pulls all of the SpaceX Falcon launches from the website
https://spaceflightnow.com/launch-schedule/ for the purposes of adding the
data to a Google calendar
"""

import re
from pprint import pprint
import requests
from bs4 import BeautifulSoup
import arrow
import datetime
from apiclient.discovery import build
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials

# scope for read/write calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
# authorize scope using credentials
credentials = ServiceAccountCredentials.from_json_keyfile_name('SpaceXLaunches-1441245ff27e.json', scopes=SCOPES)
http_auth = credentials.authorize(Http())
# create service for reading and writing to calendar with authorization obtained in above code
service = build('calendar', 'v3', http=http_auth)

def isEmpty(anyStructure):
    """This function returns whether or not a structure such as a list is empty"""
    if anyStructure:
        return False
    else:
        return True

def isSpaceXLaunch(launch):
    """This function returns whether or not a launch is a SpaceX launch based on the mission
    text containing the word 'Falcon'
    """
    # find the html tag with class="datename"
    if launch["class"] == ["datename"]:
        # if "Falcon" is part of the text in the tag with class="mission",
        # this is a SpaceX launch
        if "Falcon" in launch.select_one(".mission").string:
            return True
        else:
            return False
    else:
        return False

def getSpaceXLaunches():
    """This function gets the info for the SpaceX launches and adds them to a list of dictionaries
    for each launch
    """
    # regex to separate the launchTime string from the launchSite string
    dateLocationRegex = re.compile("^.*?:\s*(?:Approx\.\s*)?(TBD|[\d-]+)(?: GMT)?.*:\s(.*)")

    # get the html from the spaceflightnow launch schedule website
    url = "https://spaceflightnow.com/launch-schedule/"
    response = requests.get(url)
    # create BeautifulSoup parser for html
    soup = BeautifulSoup(response.text, 'html.parser')
    # create a list of "launches" where a launch is any dif element whose parent element
    # has class="entry-content"
    launches = soup.select(".entry-content > div")

    # iterate through "launches"
    # "launches" is in quotes because a launch consists of data from three sibling divs
    # each launch starts with a div whose class="datename" followed by "missiondata"
    # and finally "missdescrip"
    for launch in launches:
        # a dictionary to store information for this launch
        launchInfo = {}
        if isSpaceXLaunch(launch):
            launchInfo["launchdate"] = launch.select_one(".launchdate").string
            launchInfo["mission"] = launch.select_one(".mission").string
            # prepare and parse missiondata text with regex
            missiondata = launch.next_sibling.next_sibling.text.replace('\n', ':')
            matches = dateLocationRegex.match(missiondata)
            launchInfo["launchTime"] = matches.groups()[0]
            launchInfo["launchSite"] = matches.groups()[1]
            missdescrip = launch.next_sibling.next_sibling.next_sibling.next_sibling.text
            launchInfo["missdescrip"] = missdescrip
            # strip "NET" from launchdate if it is present and add it to the beginning of
            # missdescrip so that the information is not lost, but it does not impact date
            # parsing later
            if "NET" in launchInfo["launchdate"]:
                launchInfo["missdescrip"] = launchInfo["launchdate"] + ": " + missdescrip
                launchInfo["launchdate"] = str(launchInfo["launchdate"].replace("NET", "")).strip()

        # if this was a SpaceX launch, give the dictionary to the next function with yield
        # this saves memory by not creating a giant all at once and instead processing each
        # item as it is created
        if not isEmpty(launchInfo):
            yield launchInfo

def createGoogleCalendarEvent():
    """This function parses the launchInfo for the SpaceX launch into an event to add to a Google calendar
    and adds the event to a Google calendar
    """

    # list to capture launches that aren't being parsed properly for a calendar event
    errors = []

    # initialize previousDate to two years ago so that we know it will be smaller than
    # the date of the first launch in the list
    previousDate = arrow.now().replace(year = arrow.now().year - 2)
    # get the current year
    theYear = arrow.now().year
    # add or update a calendar event for each SpaceX launch
    for launch in getSpaceXLaunches():
        theEvent = {
            'summary':  launch["mission"],
            'location': launch["launchSite"],
            'description': launch["missdescrip"]
        }
        # remove the "." from the date if the month is abbreviated
        splitDate = launch["launchdate"].split(".")
        # if the length of splitDate is not 2, the month may not be abbreviated or
        # the date might not be specific
        if len(splitDate) != 2:
            # try splitting the date on a " "
            splitDate = launch["launchdate"].split(" ")
            # if the length of splitDate is still not equal to 2, the date is not valid
            # if the length is equal to 2, but splitDate[1] is not all digits or 
            # the length of splitDate[1] is greater than 2, then this is not a valid date
            if len(splitDate) != 2 or not splitDate[1].isdigit() or len(splitDate[1]) > 2:
                errors.append(launch)
                continue
            # if this is a valid date, add a " " before the number in splitDate[1]
            # so that it matches the format of the dates that were split on a "."
            splitDate[1] = " " + splitDate[1]
        # join the two strings in splitDate back together to make a date string
        # take only the first 3 characters of splitDate[0] to match the abbreviations
        # that arrow uses for months
        theDate = splitDate[0][:3] + splitDate[1]
        
        # if the launchTime is TBD, set the launchTime to midnight and set the flag
        # for creating an all-day event
        allday = False
        if launch["launchTime"] == "TBD":
            launch["launchTime"] = "0000"
            allday = True

        # concatenate the launchdate with the launchTime to get a string that arrow
        # can parse to a datetime
        startDatetimeString = theDate + " " + launch["launchTime"]
        startDatetime = arrow.get(startDatetimeString, 'MMM D HHmm')
        # add the correct year to startDatetime
        startDatetime = startDatetime.replace(year = theYear)
        # if startDatetime is less than previousDate, our list of launches has wrapped
        # to the next year
        if startDatetime < previousDate:
            # correct the year for startDatetime
            theYear = theYear + 1
            startDatetime = startDatetime.replace(year = theYear)
        # set previousDate to the startDatetime for this launch
        previousDate = startDatetime

        # if launchTime is TBD, the start should only have a date to create an all-day
        # event, otherwise a datetime is used for a specific launch time
        if allday:
            theEvent["start"] = {"date": startDatetime.format("YYYY-MM-DD")}
        else:
            theEvent["start"] = {"dateTime": startDatetime.isoformat()}
        
        # the end of the event is the same as the start
        # ******* may consider changing this to reflect the launch window if present ********
        theEvent["end"] = theEvent["start"]

        # print the events that are being added to the calendar to the console for debugging
        print("\n\n")
        pprint(theEvent)
        
        # add the event to the calendar
        e = service.events().insert(calendarId='jtt4kee7pdt4sg9bpj3basjpkk@group.calendar.google.com', body=theEvent).execute()

    #Error Printing for Debugging
    # print("\n\n*******ERROR*******")
    # pprint(errors)

def main():
    # adds SpaceX launches to the SpaceXLaunch calendar
    createGoogleCalendarEvent()

if __name__ == "__main__":
    main()
