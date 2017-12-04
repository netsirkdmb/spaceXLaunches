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
credentials = ServiceAccountCredentials.from_json_keyfile_name('SpaceXLaunches-54ed254ee8b1.json', scopes=SCOPES)
http_auth = credentials.authorize(Http())
# create service for reading and writing to calendar with authorization obtained in above code
service = build('calendar', 'v3', http=http_auth)

def isEmpty(anyStructure):
    """This function returns whether or not a structure such as a list is empty"""
    if anyStructure:
        return False
    else:
        return True

def containsFalcon(missionText):
    if "Falcon" in missionText or "falcon" in missionText:
        return True
    else:
        return False

def isSpaceXLaunch(launch):
    """This function returns whether or not a launch is a SpaceX launch based on the mission
    text containing the word 'Falcon'
    """
    # find the html tag with class="datename"
    if launch["class"] == ["datename"]:
        missionText = launch.select_one(".mission").string
        # if "Falcon" or "falcon" is part of the text in the tag with class="mission",
        # this is a SpaceX launch, return true
        return containsFalcon(missionText)
    # html tag isn't class="datename"
    else:
        return False

def getSpaceXLaunches():
    """This function gets the info for the SpaceX launches and adds them to a list of dictionaries
    for each launch
    """
    # get the html from the spaceflightnow launch schedule website
    url = "https://spaceflightnow.com/launch-schedule/"
    response = requests.get(url)
    # return the parsed SpaceX launches
    return parseLaunchSchedule(response.text)

def extractLaunchesFromSoup(soup):
    """This function gets all of the divs with launch info out of the html"""
    return soup.find_all("div", class_=["datename", "missiondata", "missdescrip"])

def parseLaunchSchedule(html):
    # regex to separate the launchTime string from the launchSite string
    dateLocationRegex = re.compile("^.*?:\s*(?:Approx\.\s*)?(TBD|[\d-]+)(?: GMT)?.*:\s(.*)")

    # create BeautifulSoup parser for html
    soup = BeautifulSoup(html, 'html.parser')
    # create a list of "launches" where a launch is any dif element whose parent element
    # has class="entry-content"
    launches = extractLaunchesFromSoup(soup)
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
            launchInfo["missdescrip"] = missdescrip + " www.spacex.com/webcast"
            # strip "NET" from launchdate if it is present and add it to the beginning of
            # missdescrip so that the information is not lost, but it does not impact date
            # parsing later
            if "NET" in launchInfo["launchdate"]:
                launchInfo["missdescrip"] = launchInfo["launchdate"] + ": " + missdescrip
                launchInfo["launchdate"] = str(launchInfo["launchdate"].replace("NET", "")).strip()
        else:
            pprint("**** not a SpaceX launch: " + str(launch))
        # if this was a SpaceX launch, give the dictionary to the next function with yield
        # this saves memory by not creating a giant all at once and instead processing each
        # item as it is created
        if not isEmpty(launchInfo):
            yield launchInfo

def createCorrectDatetime(datetimeString, theYear, previousDate, startDatetime = None):
    # convert the datetime string to a datetime
    theDatetime = arrow.get(datetimeString, 'MMM D HHmm')
    # add the correct year to startDatetime
    theDatetime = theDatetime.replace(year = theYear)

    # if this is an end time, make sure the day is correct if the launch window spans a date change
    if startDatetime != None and theDatetime < startDatetime:
        theDatetime = theDatetime.shift(days=+1)
    # if startDatetime is less than previousDate, our list of launches has wrapped
    # to the next year
    elif theDatetime < previousDate:
        # correct the year for startDatetime
        theYear = theYear + 1
        theDatetime = theDatetime.replace(year = theYear)
    # set previousDate to the startDatetime for this launch
    previousDate = theDatetime

    return theDatetime, previousDate, theYear

def main():
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
        wrongDateLength = len(splitDate) != 2
        if wrongDateLength:
            # try splitting the date on a " "
            splitDate = launch["launchdate"].split(" ")
            # if the length of splitDate is still not equal to 2, the date is not valid
            # if the length is equal to 2, but splitDate[1] is not all digits or 
            # the length of splitDate[1] is greater than 2, then this is not a valid date
            # note that the date may still be valid if it is something like "April 2/3"
            wrongDateLength = len(splitDate) != 2
            if wrongDateLength or not splitDate[1].isdigit() or len(splitDate[1]) > 2:
                # make sure the number portion of the date does not have a "/", which would make it a valid date
                if wrongDateLength or "/" not in splitDate[1]:
                    errors.append(launch)
                    continue
            # if this is a valid date, add a " " before the number in splitDate[1]
            # so that it matches the format of the dates that were split on a "."
            splitDate[1] = " " + splitDate[1]
        
        # if date number is in #/# format, figure out what to do
        if "/" in splitDate[1]:
            errors.append(launch)
            continue

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
        
        # set start and end times for launch window
        launchWindow = launch["launchTime"].split("-")
        startTime = launchWindow[0]
        if len(launchWindow) == 2:
            endTime = launchWindow[1]
        else:
            endTime = startTime

        # concatenate the launchdate with the launchTime to get a string that arrow
        # can parse to a datetime
        startDatetimeString = theDate + " " + startTime
        endDatetimeString = theDate + " " + endTime

        # correct the datetimes
        startDatetime, previousDate, theYear = createCorrectDatetime(startDatetimeString, theYear, previousDate)
        endDatetime, previousDate, theYear = createCorrectDatetime(endDatetimeString, theYear, previousDate, startDatetime)

        # if launchTime is TBD, the start should only have a date to create an all-day
        # event, otherwise a datetime is used for a specific launch time
        if allday:
            theEvent["start"] = {"date": startDatetime.format("YYYY-MM-DD")}
            theEvent["end"] = theEvent["start"]
        else:
            theEvent["start"] = {"dateTime": startDatetime.isoformat()}
            theEvent["end"] = {"dateTime": endDatetime.isoformat()}

        # print the events that are being added to the calendar to the console for debugging
        print("\n\n")
        pprint(theEvent)
        
        # add the event to the calendar
        # e = service.events().insert(calendarId='jtt4kee7pdt4sg9bpj3basjpkk@group.calendar.google.com', body=theEvent).execute()

    #Error Printing for Debugging
    print("\n\n*******ERROR*******")
    pprint(errors)

if __name__ == "__main__":
    main()
