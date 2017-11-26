import unittest
from SpaceXLaunchExtractor import *


class TestHTMLParsing(unittest.TestCase):
    def testFindAllLaunches(self):
        html = open("launchSchedule11-25-17.html").read()
        soup = BeautifulSoup(html, 'html.parser')
        launches = extractLaunchesFromSoup(soup)
        self.assertEquals(len(launches), 53)

if __name__ == '__main__':
    unitetest.main()