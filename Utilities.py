##FIX THE ENV VARIABLE THING!

import requests
import bs4
import math 
import re
import json
from google import genai
from ddgs import DDGS
from difflib import SequenceMatcher
import os
import base64
from dotenv import load_dotenv
load_dotenv()#Allows it to get the API key from the .env

class Utilities:
    def getProfReviews(self, url):
        #Get the HTML from RMP. The header is required because RMP blocks Python bots, so we must pretend to be an actual browser
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        reviewsLoadedBeforePressingButton = 5
        numberText = soup.select(".hNMvaE")

        if len(numberText) != 0:
            try:
                numberRatings = int(numberText[0].select_one('a').get_text().split()[0])#select_one selects one part of the HTML (in this case the a tag), get_text gets the text inside that tag, and the .split[0] gets just the number
            except ValueError: #Gives a ValueError when there's no ratings for the prof (it gives the "Add" from "Add A Rating" instead of a number):
                numberRatings = 0

            reviews = {}
            cursor = None #start with no cursor to get the first page

            #Get the GraphQL ID for the prof
            script = soup.find('script', string=re.compile('__RELAY_STORE__'))#soup.find() returns the first instance of a specific tag (script in this case). The string= part ensures that it returns only the script tag that contains an instance of __RELAY_STORE__. re.compile() converts the string into a regex (searching) object, so that BS4 isn't searching for a script tag whose entire contexts are exclusively __RELAY_STORE__ but just contain it.
            store_text = script.string#Remove the HTML tags and keep just the parts inside the tags (i.e. the body)
            json_str = store_text.split('window.__RELAY_STORE__ = ')[1]#There's 3 things inside the script tag. Keep just the right part (what __RELAY_STORE is = to)
            json_str = json_str[:json_str.index(';\n')]#Get the piece that ends with a semicolon (i.e. the value that window.__RELAY_STORE__ is equal to)
            store = json.loads(json_str)#Converts the JSON string into a Python dictionary. NOTE: This creates a nested dictionary, where the ID we need is the outer key and the inner stuff includes the type, legacy ID, etc.
            graphql_id = next(key for key in store.keys() if store[key].get('__typename') == 'Teacher')#next goes through an iterable object one by one. Since it's only called once here, it prints the first object. The loop creates a list, loops through each key in the outer dictionary, checks the value of the __typename entry (if existent), and if it's Teacher then we know this specific inner dictionary (and its outer key, which is the ID) is the one we want. Thus, add that key to the list

            #Add all the reviews to the reviews list
            for k in range(math.ceil(numberRatings/reviewsLoadedBeforePressingButton)):
                #Emulate clicking the more reviews button
                response = requests.post( #This is a post request because we're changing the body
                    "https://www.ratemyprofessors.com/graphql",
                    #The query tells GraphQL what we want (this is copy pasted from RMP's post request). The cursor tells GraphQL where to start from (e.g. reviews 1-5, or 6-10, etc.)
                    json={
                        "query": "query RatingsListQuery(\n  $count: Int!\n  $id: ID!\n  $courseFilter: String\n  $cursor: String\n) {\n  node(id: $id) {\n    __typename\n    ... on Teacher {\n      ...RatingsList_teacher_4pguUW\n    }\n    id\n  }\n}\n\nfragment CourseMeta_rating on Rating {\n  attendanceMandatory\n  wouldTakeAgain\n  grade\n  textbookUse\n  isForOnlineClass\n  isForCredit\n}\n\nfragment NoRatingsArea_teacher on Teacher {\n  lastName\n  ...RateTeacherLink_teacher\n}\n\nfragment ProfessorNoteEditor_rating on Rating {\n  id\n  legacyId\n  class\n  teacherNote {\n    id\n    teacherId\n    comment\n  }\n}\n\nfragment ProfessorNoteEditor_teacher on Teacher {\n  id\n}\n\nfragment ProfessorNoteFooter_note on TeacherNotes {\n  legacyId\n  flagStatus\n}\n\nfragment ProfessorNoteFooter_teacher on Teacher {\n  legacyId\n  isProfCurrentUser\n}\n\nfragment ProfessorNoteHeader_note on TeacherNotes {\n  createdAt\n  updatedAt\n}\n\nfragment ProfessorNoteHeader_teacher on Teacher {\n  lastName\n}\n\nfragment ProfessorNoteSection_rating on Rating {\n  teacherNote {\n    ...ProfessorNote_note\n    id\n  }\n  ...ProfessorNoteEditor_rating\n}\n\nfragment ProfessorNoteSection_teacher on Teacher {\n  ...ProfessorNote_teacher\n  ...ProfessorNoteEditor_teacher\n}\n\nfragment ProfessorNote_note on TeacherNotes {\n  comment\n  ...ProfessorNoteHeader_note\n  ...ProfessorNoteFooter_note\n}\n\nfragment ProfessorNote_teacher on Teacher {\n  ...ProfessorNoteHeader_teacher\n  ...ProfessorNoteFooter_teacher\n}\n\nfragment RateTeacherLink_teacher on Teacher {\n  legacyId\n  numRatings\n  lockStatus\n}\n\nfragment RatingFooter_rating on Rating {\n  id\n  comment\n  adminReviewedAt\n  flagStatus\n  legacyId\n  thumbsUpTotal\n  thumbsDownTotal\n  thumbs {\n    thumbsUp\n    thumbsDown\n    computerId\n    id\n  }\n  teacherNote {\n    id\n  }\n  ...Thumbs_rating\n}\n\nfragment RatingFooter_teacher on Teacher {\n  id\n  legacyId\n  lockStatus\n  isProfCurrentUser\n  ...Thumbs_teacher\n}\n\nfragment RatingHeader_rating on Rating {\n  legacyId\n  date\n  class\n  helpfulRating\n  clarityRating\n  isForOnlineClass\n}\n\nfragment RatingSuperHeader_rating on Rating {\n  legacyId\n}\n\nfragment RatingSuperHeader_teacher on Teacher {\n  firstName\n  lastName\n  legacyId\n  school {\n    name\n    id\n  }\n}\n\nfragment RatingTags_rating on Rating {\n  ratingTags\n}\n\nfragment RatingValues_rating on Rating {\n  helpfulRating\n  clarityRating\n  difficultyRating\n}\n\nfragment Rating_rating on Rating {\n  comment\n  flagStatus\n  createdByUser\n  teacherNote {\n    id\n  }\n  ...RatingHeader_rating\n  ...RatingSuperHeader_rating\n  ...RatingValues_rating\n  ...CourseMeta_rating\n  ...RatingTags_rating\n  ...RatingFooter_rating\n  ...ProfessorNoteSection_rating\n}\n\nfragment Rating_teacher on Teacher {\n  ...RatingFooter_teacher\n  ...RatingSuperHeader_teacher\n  ...ProfessorNoteSection_teacher\n}\n\nfragment RatingsList_teacher_4pguUW on Teacher {\n  id\n  legacyId\n  lastName\n  numRatings\n  school {\n    id\n    legacyId\n    name\n    city\n    state\n    avgRating\n    numRatings\n  }\n  ...Rating_teacher\n  ...NoRatingsArea_teacher\n  ratings(first: $count, after: $cursor, courseFilter: $courseFilter) {\n    edges {\n      cursor\n      node {\n        ...Rating_rating\n        id\n        __typename\n      }\n    }\n    pageInfo {\n      hasNextPage\n      endCursor\n    }\n  }\n}\n\nfragment Thumbs_rating on Rating {\n  id\n  comment\n  adminReviewedAt\n  flagStatus\n  legacyId\n  thumbsUpTotal\n  thumbsDownTotal\n  thumbs {\n    computerId\n    thumbsUp\n    thumbsDown\n    id\n  }\n  teacherNote {\n    id\n  }\n}\n\nfragment Thumbs_teacher on Teacher {\n  id\n  legacyId\n  lockStatus\n  isProfCurrentUser\n}\n",
                        "variables": {"count": 5, "id": graphql_id, "courseFilter": None, "cursor": cursor}
                    },
                    headers={"User-Agent": "Mozilla/5.0"}#So it doesn't think we're a Python script
                )
                data = response.json()#Decodes the JSON string into a Python dictionary
                
                # Extract comments from the response
                edges = data['data']['node']['ratings']['edges']#The dictionary with its outer key that was the ID we accessed earlier contains many things (ex. at end). The "edges" are the reviews, so this variable contains a list of reviews.
                
                for edge in edges:
                    course = edge['node']['class']
                    reviews.setdefault(course, []).append(edge['node']['comment'])#setdefault checks if a key of that name exists. If not, it creates it with an empty list and appends the review to it. If yes, it returns the value (the current list), and appends the review to it.
                    #Ex. {"1ZA3":  ["Great prof, very hard exam", "Very clear lectures"], "1ZC3": ["Very confusing lectures, told too many jokes", "Loved his teaching style"]}
                # Update cursor for next page
                cursor = data['data']['node']['ratings']['pageInfo']['endCursor']

            return reviews
        return []

    def generateResponse(self, data, className = None):
        KEY = os.getenv("GEMINI_API_KEY")
        DATA = json.dumps(data)

        if className != None:
            prompt = f"""Read this list of reviews and generate a concensus about this class. The class name is {className}.
                    Keep it to one paragraph and accurate, and use an authoritative tone.
                    Use your best judgment on what could be the same class (i.e. since all classes are from the same dept., ENGINEER 1P13 and 1P13 are the same class). 
                    MAKE SURE TO ENSURE THAT YOU GIVE AN OVERVIEW ON THE CLASS, not just of the different profs teaching it. Ensure that you add a sentence on the course's difficulty. DO NOT MENTION SPECIFIC PROFS.
                    Include roughly equal portions on the good and bad. {DATA}"""
        else:
            prompt = f"""Read this list of reviews and generate a concensus about this professor.
                         Keep it to one paragraph and accurate, and use an authoritative tone.
                         Include roughly equal portions on the good and bad. {DATA}
            """
            
        client = genai.Client()

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt
        )

        return response.text
    
    def getURL(self, uni, prof):
        #Search the web for the specific prof, then get that HREF (not the most reliable method but it seems to work)
        searchObj = DDGS()
        results = searchObj.text(f'"{uni}", "{prof}", "Rate My Professors"', max_results=1)
        url = results[0]["href"]
        
        return url
    
    def getAllIds(self, uni, dept):
        #Get the school ID
        response = requests.post(
            "https://www.ratemyprofessors.com/graphql",
            json={
                "query": """
                    query GetSchoolID($schoolName: String!) {
                        newSearch {
                            schools(query: { text: $schoolName }) {
                                edges {
                                    node {
                                        id
                                        legacyId
                                        name
                                    }
                                }
                            }
                        }
                    }
                """,
                "variables": {"schoolName": uni}
            },
            headers={"Authorization": "Basic dGVzdDp0ZXN0", "User-Agent": "Mozilla/5.0"}
        )
        data = response.json()
        schoolEncoded = data["data"]["newSearch"]["schools"]["edges"][0]["node"]["id"]  # e.g. "U2Nob29sLTE0NDA="
        schoolId = data["data"]["newSearch"]["schools"]["edges"][0]["node"]["legacyId"]  # e.g. 1440

        #Get the department names and IDs
        response = requests.post(
                    "https://www.ratemyprofessors.com/graphql",
                    json={
                        "query": """
                            query GetSchoolAndDepartments($schoolName: String!, $query: TeacherSearchQuery!) {
                                newSearch {
                                    schools(query: { text: $schoolName }) {
                                        edges {
                                            node {
                                                id
                                                legacyId
                                                name
                                            }
                                        }
                                    }
                                    teachers(query: $query, first: 1, after: "") {
                                        filters {
                                            field
                                            options {
                                                value
                                                id
                                            }
                                        }
                                    }
                                }
                            }
                        """,
                        "variables": {
                            "schoolName": f"{uni}",
                            "query": {
                                "text": "",
                                "schoolID": schoolEncoded,
                                "fallback": True
                            }
                        }
                    },
                    headers={
                        "Authorization": "Basic dGVzdDp0ZXN0",
                        "User-Agent": "Mozilla/5.0"
                    }
                )
        data = response.json()

        #Get the school's ID and all the department ID's
        allDeptIds = []
        for i in data["data"]["newSearch"]["teachers"]["filters"][0]["options"]:
            allDeptIds.append(i)#Returns a list of dicts. E.g. [{"id": "ABCD", "value": "accounting"}, {"id": "EFGH", "value": "anthropology"}]
        
        #Find the department ID corresponding to the user's department
        dept = dept.lower()
        best_similarity = 0.8
        best_id = None
        for i in allDeptIds:
            value = i.get("value", "").lower()
            id_b64 = i.get("id")

            # Skip entries with no ID
            if not id_b64:
                continue

            # Compute similarity score of current ID vs. user input
            similarity = SequenceMatcher(None, dept, value).ratio()

            # Only update if it's better than the current best
            if similarity >= best_similarity:
                try:
                    decoded = base64.b64decode(id_b64).decode("utf-8")
                except Exception:
                    continue  # skip invalid Base64

                if decoded:
                    best_similarity = similarity
                    best_id = decoded

        return schoolId, best_id
    
    def getAllProfURL(self, uni, dept):
        schoolID, deptID = self.getAllIds(uni, dept)
        deptIDNum = deptID.split("-")[1]#Since deptID is currently in format "Department-x"
        filteredURL = f"https://www.ratemyprofessors.com/search/professors/{schoolID}?q=*&did={deptIDNum}"

        response = requests.get(filteredURL, headers={"User-Agent": "Mozilla/5.0"})
        soup = bs4.BeautifulSoup(response.content, "html.parser")
        profs = soup.find_all("a", class_="TeacherCard__StyledTeacherCard-syjs0d-0")
        
        profURLs = []
        for i in profs:
            profURLs.append(f"https://www.ratemyprofessors.com{i["href"]}")

        #Get the JSON object that has the required data 
        script = soup.find('script', string=re.compile('__RELAY_STORE__'))#Get the __RELAY_STORE__ data (inside the script tag)
        store_text = script.string
        json_str = store_text.split('window.__RELAY_STORE__ = ')[1] #Get JUST that data (it was split into the window._RELAY_STORE__ tag and the actual data)
        json_str = json_str[:json_str.index(';\n')]#Gives us just the JSON object that window.__RELAY_STORE__ is equal to
        store = json.loads(json_str) #Convert that string into a Python JSON object

        # Find the connection object to get the starting pageInfo
        for v in store.values():
            if v.get('__typename') == 'TeacherSearchConnectionConnection':
                connection = v#Gives us the entire dictionary inside TeacherSearchConnectionConnection
                break

        pageInfoKey = connection['pageInfo']['__ref']
        pageInfo = store[pageInfoKey]

        has_next_page = pageInfo['hasNextPage']
        cursor = pageInfo['endCursor']

        #Encode the school and dept ID's so they're in RMP's format
        schoolEncoded = base64.b64encode(f"School-{schoolID}".encode()).decode()
        deptEncoded   = base64.b64encode(deptID.encode()).decode()

        while has_next_page:
            response = requests.post(
                "https://www.ratemyprofessors.com/graphql",
                json={
                    "query": """
                        query GetProfs($query: TeacherSearchQuery!, $cursor: String) {
                            newSearch {
                                teachers(query: $query, first: 5, after: $cursor) {
                                    edges {
                                        node {
                                            legacyId
                                        }
                                    }
                                    pageInfo {
                                        hasNextPage
                                        endCursor
                                    }
                                }
                            }
                        }
                    """,
                    "variables": {
                        "query": {
                            "text": "",
                            "schoolID": schoolEncoded,
                            "departmentID": deptEncoded,
                            "fallback": True
                        },
                        "cursor": cursor
                    }
                },
                headers={"Authorization": "Basic dGVzdDp0ZXN0", "User-Agent": "Mozilla/5.0"}
            )

            data = response.json()
            teachers = data["data"]["newSearch"]["teachers"]

            for edge in teachers["edges"]:
                profURLs.append(f"https://www.ratemyprofessors.com/professor/{edge['node']['legacyId']}")

            has_next_page = teachers["pageInfo"]["hasNextPage"]
            cursor = teachers["pageInfo"]["endCursor"]

        return profURLs
    
    def getReviewsAndResponse(self, uni, dept, className):
        allURL = self.getAllProfURL(uni, dept)
        allDeptReviews = []

        for i in allURL:
            reviews = self.getProfReviews(i)
            allDeptReviews.append(reviews)
        
        geminiResponse = self.generateResponse(allDeptReviews, className) 
        return geminiResponse

"""
{
    "data": {
        "node": {
            "__typename": "Teacher",
            "id": "VGVhY2hlci01MTc3MDY=",
            "ratings": {
                "edges": [
                    {
                        "cursor": "YXJyYXljb25uZWN0aW9uOjU=",
                        "node": {
                            "comment": "Great professor, explains concepts very clearly.",
                            "helpfulRating": 5,
                            "clarityRating": 5,
                            "difficultyRating": 2,
                            "grade": "A+",
                            "wouldTakeAgain": 1
                        }
                    },
                    {
                        "cursor": "YXJyYXljb25uZWN0aW9uOjY=",
                        "node": {
                            "comment": "Tests are harder than the lectures suggest.",
                            "helpfulRating": 3,
                            "clarityRating": 3,
                            "difficultyRating": 4,
                            "grade": "B",
                            "wouldTakeAgain": 0
                        }
                    },
                    {
                        "cursor": "YXJyYXljb25uZWN0aW9uOjc=",
                        "node": {
                            "comment": "Funny guy but hard to follow sometimes.",
                            "helpfulRating": 4,
                            "clarityRating": 3,
                            "difficultyRating": 3,
                            "grade": "A-",
                            "wouldTakeAgain": 1
                        }
                    }
                ],
                "pageInfo": {
                    "hasNextPage": true,
                    "endCursor": "YXJyYXljb25uZWN0aW9uOjc="
                }
            }
        }
    }
}
"""