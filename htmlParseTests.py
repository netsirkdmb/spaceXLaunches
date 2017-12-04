import unittest
from SpaceXLaunchExtractor import *


class TestHTMLParsing(unittest.TestCase):
    def testFindAllLaunches(self):
        with open("launchSchedule11-25-17.html") as f:
            html = f.read()
            soup = BeautifulSoup(html, 'html.parser')
            launches = extractLaunchesFromSoup(soup)
            self.assertEqual(len(launches), 159)

    def testFindAllFalconLaunches(self):
        with open("launchSchedule11-25-17.html") as f:
            html = f.read()
            soup = BeautifulSoup(html, 'html.parser')
            launches = extractLaunchesFromSoup(soup)
            spaceXLaunches = list(filter(isSpaceXLaunch, launches))
            self.assertEqual(len(spaceXLaunches), 15)
    
    def testContainsFalconUppercase(self):
        mission = "this is a Falcon launch"
        self.assertTrue(containsFalcon(mission))

    def testContainsFalconLowercase(self):
        mission = "this is a falcon launch"
        self.assertTrue(containsFalcon(mission))
    
    def testContainsFalconFalse(self):
        mission = "this is an Atlas launch"
        self.assertFalse(containsFalcon(mission))


class TestSplitDate(unittest.TestCase):
    pass

badDateList = ["TBD", "January", "First Half of 2018", "Mid-2018"]
goodDateList = ["Dec. 2", "Dec. 7/8", "April 25", "March 13/14", "Early 2018", "1st Quarter", "Late December"]

for i, goodDate in enumerate(goodDateList):
    def testGoodDate(self):
        self.assertIsNotNone(splitLaunchDate(goodDate), "splitDate('{}') should not be None".format(goodDate))
    setattr(TestSplitDate, "testValidSplitDate{}".format(i), testGoodDate)

for i, badDate in enumerate(badDateList):
    def testBadDate(self):
        self.assertIsNone(splitLaunchDate(badDate), "splitDate('{}') should be None".format(badDate))
    setattr(TestSplitDate, "testInvalidSplitDate{}".format(i), testBadDate)
            

class TestCheckMonth(unittest.TestCase):
    pass

badMonthList = ["Early", "1st", "Late"]
goodMonthList = ["Dec", "April", "March"]

for i, goodMonth in enumerate(goodMonthList):
    def testGoodMonth(self):
        self.assertIsNotNone(checkMonth(goodMonth), "checkMonth('{}') should not be None".format(goodMonth))
    setattr(TestCheckMonth, "testValidCheckMonth{}".format(i), testGoodMonth)

for i, badMonth in enumerate(badMonthList):
    def testBadMonth(self):
        self.assertIsNone(checkMonth(badMonth), "checkMonth('{}') should be None".format(badMonth))
    setattr(TestCheckMonth, "testInvalidCheckMonth{}".format(i), testBadMonth)


if __name__ == '__main__':
    unitetest.main()
    