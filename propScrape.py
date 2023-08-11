from distutils.fancy_getopt import wrap_text
from bs4 import BeautifulSoup
import csv
from datetime import timedelta, date
from matplotlib.pyplot import title
import numpy
import os
import re
from re import S
import requests
import selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import string
import time
from tkcalendar import DateEntry
import tkinter
from tkinter import simpledialog




class GalvestonProbateCSV:

    array = []
    dateLowerBound = ''
    dateUpperBound = ''

    #private

    def __init__(self):
        self.array.append(GalvestonProbateParameters.getHeader())

    #def __init__(self, manual_parameters_placeholder): overloaded constructor for driver to use
    #    pass
    def NoGUI(self):
        pass

    def GUI(self):
        def execute(*args):
            self.dateLowerBound = _dateLowerBound.get_date()
            self.dateUpperBound = _dateUpperBound.get_date()
            self.search()
            status.config(text='close to update CSV')

        window = tkinter.Tk()
        window.geometry("370x220")

        _dateLowerBound = DateEntry(window, selectmode = 'day')
        _dateLowerBound.grid(row = 1, column = 1, padx = 5, pady = 15)

        _dateUpperBound = DateEntry(window, selectmode = 'day')
        _dateUpperBound.grid(row = 1, column = 3, padx = 5, pady = 15)

        searchButton = tkinter.Button(window, text='Search', command = lambda:execute(), width=10)
        searchButton.grid(row = 2, column = 1, pady = 15)

        to = tkinter.Label(window, text = 'to', width=10)
        to.grid(row = 1, column = 2)

        status = tkinter.Label(window, text = '', width=18)
        status.grid(row=3, column=2, pady = 15)

        window.mainloop()

    def search(self):
        #driverOptions = Options()
        #driverOptions.add_argument('headless')
        #driver = webdriver.Chrome(options = driverOptions)
        driver = webdriver.Chrome()
        driver.get('https://publicaccess.co.galveston.tx.us/default.aspx')

        #default page
        button1 = driver.find_element(By.LINK_TEXT, 'Probate Case Records')
        button1.click()

        #search page
        button2 = driver.find_element(By.ID, 'DateFiled')
        button2.click()
        dateBox1 = driver.find_element(By.ID, 'DateFiledOnAfter')
        dateBox1.send_keys(self.dateLowerBound.strftime("%m/%d/%Y"))
        dateBox1 = driver.find_element(By.ID, 'DateFiledOnBefore')
        dateBox1.send_keys(self.dateUpperBound.strftime("%m/%d/%Y"))
        button3 = driver.find_element(By.NAME, 'SearchSubmit')
        button3.click()

        #results page

        #check here if max results reached. if so, divide the time in two and instantiate one object with each of them then add array to current
        resultsHTML = driver.page_source
        resultsSoup = BeautifulSoup(resultsHTML, 'html.parser')
        if(resultsSoup.find_all(string = '--- The search resulted in too many matches to display.  Narrow the search by entering more precise criteria. ---')):
            self.split()
            driver.close()
        elif(not driver.find_elements(By.PARTIAL_LINK_TEXT, '-')):
            pass
        else:
            entries = driver.find_elements(By.PARTIAL_LINK_TEXT, '-')
            for entry in entries:
                newURL = entry.get_attribute('href')
                driver.execute_script("window.open('');")
                driver.switch_to.window(driver.window_handles[1])
                driver.get(newURL)
                html = driver.page_source

                gpp = GalvestonProbateParameters(html)
                if(gpp.getArray()):
                    self.array.append(gpp.getArray())

                driver.close()
                driver.switch_to.window(driver.window_handles[0])

    def split(self):
        midDate = self.dateLowerBound + (self.dateUpperBound - self.dateLowerBound)/2
        midDatePlusOne = midDate + timedelta(days = 1)
        csv1 = GalvestonProbateCSV()
        csv2 = GalvestonProbateCSV()
        csv1.dateLowerBound = self.dateLowerBound
        csv1.dateUpperBound = midDate
        csv2.dateLowerBound = midDatePlusOne
        csv2.dateUpperBound = self.dateUpperBound
        csv1.search()
        csv2.search()
        print(csv1.array)
        print(csv2.array)
        csv1.array.pop(0) #pops headers
        csv2.array.pop(0)
        for i in range(0, len(csv1.array)):
            self.array.append(csv1.array[i])
        for i in range(0, len(csv2.array)):
            self.array.append(csv2.array[i])

    def getCSV(self):
        numpyArr = numpy.asarray(self.array)
        if(os.path.isfile('output.csv')):
            os.unlink('output.csv')
        with open('output.csv', 'w', newline='') as file:
            csvWriter = csv.writer(file, delimiter=',')
            csvWriter.writerows(numpyArr)
        file.close()





class GalvestonProbateParameters:

    array = [''] * 14 #how to make these member variables priv? #how do u do references in python
    HTML = ""

    #private

    def __init__(self, _HTML):
        self.HTML = _HTML
        self.parse()

    def parse(self) -> None: #allows array creation if checks satisfied
        soup = BeautifulSoup(self.HTML, 'html.parser')
        if(
            (self.hasApplicant(soup)) and
            (not self.hasMultipleApplicants(soup)) and
            (not self.isWard(soup)) and 
            (self.hasDecedentAddress(soup)) and
            (self.hasApplicantAddress(soup)) and
            (not self.isSameAddress(soup))
        ):
            self.array = [''] * 14
            self.makeArray(soup)
        else:
            self.array = None

    def makeArray(self, inputSoup: BeautifulSoup) -> None: #handles creation of array from soup obj
        decedentAddress = inputSoup.find('th', string = 'Decedent').find_parent().find_next_sibling('tr').find('td')
        applicant = inputSoup.find('th', string = 'Applicant')
        applicantAddress = applicant.find_parent().find_next_sibling('tr').find('td')

        #("Decedent Address") #[0]
        if(len(decedentAddress.contents) == 4): #2 line address
            self.array[0] = str(decedentAddress.contents[0]).replace(u'\xa0', '')
        if(len(decedentAddress.contents) == 6): #3 line address (attaches unit number to address line)
            self.array[0] = str(decedentAddress.contents[0]).replace(u'\xa0', '') + ' ' + str(decedentAddress.contents[2]).replace(u'\xa0', '')

        #("Decedent City") #[1]
        if(len(decedentAddress.contents) == 4):
            self.array[1] = str(decedentAddress.contents[2]).replace(u'\xa0', '').split(',')[0]
        if(len(decedentAddress.contents) == 6):
            self.array[1] = str(decedentAddress.contents[4]).replace(u'\xa0', '').split(',')[0]

        #("Decedent State") #[2]
        self.array[2] = 'TX'
        #self.array[2] = str(decedentAddress.contents[2]).replace(u'\xa0', '').split(',')[1].split(' ')[1]

        #("Decedent Zip Code") #[3]
        if(len(decedentAddress.contents) == 4):
            self.array[3] = str(decedentAddress.contents[2]).replace(u'\xa0', '').split(',')[1].split(' ')[2]
        if(len(decedentAddress.contents) == 6):
            self.array[3] = str(decedentAddress.contents[4]).replace(u'\xa0', '').split(',')[1].split(' ')[2]

        #("Decedent County") #[4]
        self.array[4] = 'Galveston County'

        #("Applicant Name First") #[5]
        self.array[5] = str(applicant.find_next_sibling('th').contents[0]).replace(u'\xa0', '').split(', ')[1]
        
        #("Applicant Name Last") #[6]
        self.array[6] = str(applicant.find_next_sibling('th').contents[0]).replace(u'\xa0', '').split(', ')[0]

        #("Applicant Address") #[7]
        if(len(applicantAddress.contents) == 4): #2 line address
            self.array[7] = str(applicantAddress.contents[0]).replace(u'\xa0', '')
        if(len(applicantAddress.contents) == 6): #3 line address (attaches unit number to address line)
            self.array[7] = str(applicantAddress.contents[0]).replace(u'\xa0', '') + ' ' + str(applicantAddress.contents[2]).replace(u'\xa0', '')

        #("Applicant City") #[8]
        if(len(applicantAddress.contents) == 4):
            self.array[8] = str(applicantAddress.contents[2]).replace(u'\xa0', '').split(',')[0]
        if(len(applicantAddress.contents) == 6):
            self.array[8] = str(applicantAddress.contents[4]).replace(u'\xa0', '').split(',')[0]

        #("Applicant State") #[9]
        if(len(applicantAddress.contents) == 4):
            self.array[9] = str(applicantAddress.contents[2]).replace(u'\xa0', '').split(',')[1].split(' ')[1]
        if(len(applicantAddress.contents) == 6):
            self.array[9] = str(applicantAddress.contents[4]).replace(u'\xa0', '').split(',')[1].split(' ')[1]

        #("Applicant Zip Code") #[10]
        if(len(applicantAddress.contents) == 4):
            self.array[10] = str(applicantAddress.contents[2]).replace(u'\xa0', '').split(',')[1].split(' ')[2]
        if(len(applicantAddress.contents) == 6):
            self.array[10] = str(applicantAddress.contents[4]).replace(u'\xa0', '').split(',')[1].split(' ')[2]

        #("Date Filed") #[11]
        self.array[11] = inputSoup.find('th', string = 'Date Filed:').find_next_sibling().b.contents[0]
        
        #("Case Number") #[12]
        self.array[12] = inputSoup.find(string = re.compile('Case No.')).find_parent().span.contents[0] #inputSoup.find('div', string = 'Case No.')
        
        #("Different States") #[13] #reliant on checks and info obtained in the earlier parts of array
        self.array[13] = self.isDifState(inputSoup)

    def hasApplicant(self, inputSoup: BeautifulSoup) -> bool:
        if(inputSoup.find('th', string = 'Applicant')):
            return True
        else:
            return False

    def isSameAddress(self, inputSoup: BeautifulSoup) -> bool: #dont store if false
        decedentAddress = inputSoup.find('th', string = 'Decedent').find_parent().find_next_sibling('tr').find('td')
        applicantAddress = inputSoup.find('th', string = 'Applicant').find_parent().find_next_sibling('tr').find('td')
        if(str(decedentAddress.contents[0]).replace(u'\xa0', '') == str(applicantAddress.contents[0]).replace(u'\xa0', '')): #compares raw strings
            if(str(decedentAddress.contents[2]).replace(u'\xa0', '') == str(applicantAddress.contents[2]).replace(u'\xa0', '')):
                return True
        return False

    def hasDecedentAddress(self, inputSoup: BeautifulSoup) -> bool: #dont store if false
        tag = inputSoup.find('th', string = 'Decedent')
        if(tag):
            address = tag.find_parent().find_next_sibling('tr')
            if len(address.find_all('br')) >= 2: #if address has two lines
                return True
        else:
            return False

    def hasApplicantAddress(self, inputSoup: BeautifulSoup) -> bool:
        tag = inputSoup.find('th', string = 'Applicant')
        if(tag):
            address = tag.find_parent().find_next_sibling('tr')
            if len(address.find_all('br')) >= 2: #if address has two lines
                return True
        else:
            return False

    def hasMultipleApplicants(self, inputSoup: BeautifulSoup) -> bool: #dont store if true
        if(len(inputSoup.find_all('th', string = 'Applicant')) > 1):
            return True
        else:
            return False

    def isWard(self, inputSoup: BeautifulSoup) -> bool: #dont store if true
        if(
            (inputSoup.find(string = 'Ward')) and
            (not inputSoup.find(string = 'Decedent'))
        ):
            return True
        else:
            return False

    def isDifState(self, inputSoup: BeautifulSoup) -> bool:
        applicantAddress = inputSoup.find('th', string = 'Applicant').find_parent().find_next_sibling('tr').find('td')
        if(len(applicantAddress.contents) == 4):
            if(str(applicantAddress.contents[2]).replace(u'\xa0', '').split(',')[1].split(' ')[1] != 'TX'): #assumed that every decedent lives in TX
                return True
        if(len(applicantAddress.contents) == 6):
            if(str(applicantAddress.contents[4]).replace(u'\xa0', '').split(',')[1].split(' ')[1] != 'TX'): #assumed that every decedent lives in TX
                return True
        return False

    #public

    def getArray(self): #-> []:
        if self.array:
            return self.array

    @staticmethod
    def getHeader(): #-> []:
        header_array = []

        header_array.append("Decedent Address") #[0]
        header_array.append("Decedent City") #[1]
        header_array.append("Decedent State") #[2]
        header_array.append("Decedent Zip Code") #[3]
        header_array.append("Decedent County") #[4]
        header_array.append("Applicant Name First") #[5]
        header_array.append("Applicant Name Last") #[6]
        header_array.append("Applicant Address") #[7]
        header_array.append("Applicant City") #[8]
        header_array.append("Applicant State") #[9]
        header_array.append("Applicant Zip Code") #[10]

        header_array.append("Date Filed") #[11]
        header_array.append("Case Number") #[12]
        header_array.append("Different States") #[13]

        return header_array




def main():
    csv = GalvestonProbateCSV()
    csv.GUI()
    #with open("Search.html") as fp:
    #    soup = BeautifulSoup(fp,'html.parser')

    #find <tr id="trSearchBy"> #id for the tr
    #insert "checked = "checked"" within <input = ... id = "DateFiled">

    #print(soup)

    csv.getCSV()

main()