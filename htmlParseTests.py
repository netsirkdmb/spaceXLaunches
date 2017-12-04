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


if __name__ == '__main__':
    unitetest.main()
    