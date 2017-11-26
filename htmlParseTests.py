import unittest
from SpaceXLaunchExtractor import *


class TestHTMLParsing(unittest.TestCase):
    def testFindAllLaunches(self):
        with open("launchSchedule11-25-17.html") as f:
            html = f.read()
            soup = BeautifulSoup(html, 'html.parser')
            launches = extractLaunchesFromSoup(soup)
            self.assertEqual(len(launches), 159)


if __name__ == '__main__':
    unitetest.main()
    