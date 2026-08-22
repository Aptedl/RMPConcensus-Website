## NEXT: ADD THE BUTTON TO GET DEPT. RATINGS IN HTML

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
import matplotlib.pyplot as plt
import mpld3
from dotenv import load_dotenv
load_dotenv()#Allows it to get the API key from the .env

class Professor:
    def __init__(self, url: str = None, reviews: list[str] = [], rating: float = 0.0, firstName: str = "", lastName: str = "", numRatings: int = 0, difficulty: int = 0):
        self.url = url
        self.reviews = reviews
        self.rating = rating
        self.firstName = firstName
        self.lastName = lastName
        self.numRatings = numRatings
        self.difficulty = difficulty

class Utilities:
    def getAllProfURL(self, uni, dept):
        schoolID, deptID = self.getAllIds(self, uni, dept)
        deptIDNum = deptID.split("-")[1]#Since deptID is currently in format "Department-x"
        filteredURL = f"https://www.ratemyprofessors.com/search/professors/{schoolID}?q=*&did={deptIDNum}"

        response = requests.get(filteredURL, headers={"User-Agent": "Mozilla/5.0"})
        soup = bs4.BeautifulSoup(response.content, "html.parser")
        profs = soup.find_all("a", class_="TeacherCard__StyledTeacherCard-syjs0d-0")
        
        profURLs = []
        for i in profs:
            profURLs.append(Professor(url=f"https://www.ratemyprofessors.com{i["href"]}"))

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
                profURLs.append(Professor(url = f"https://www.ratemyprofessors.com/professor/{edge['node']['legacyId']}"))

            has_next_page = teachers["pageInfo"]["hasNextPage"]
            cursor = teachers["pageInfo"]["endCursor"]

        return profURLs

    def getProfRatings(self, prof):
        #Get the HTML from RMP. The header is required because RMP blocks Python bots, so we must pretend to be an actual browser
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(prof.url, headers=headers)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        #Get the GraphQL ID for the prof
        script = soup.find('script', string=re.compile('__RELAY_STORE__'))#soup.find() returns the first instance of a specific tag (script in this case). The string= part ensures that it returns only the script tag that contains an instance of __RELAY_STORE__. re.compile() converts the string into a regex (searching) object, so that BS4 isn't searching for a script tag whose entire contexts are exclusively __RELAY_STORE__ but just contain it.
        store_text = script.string#Remove the HTML tags and keep just the parts inside the tags (i.e. the body)
        json_str = store_text.split('window.__RELAY_STORE__ = ')[1]#There's 3 things inside the script tag. Keep just the right part (what __RELAY_STORE is = to)
        json_str = json_str[:json_str.index(';\n')]#Get the piece that ends with a semicolon (i.e. the value that window.__RELAY_STORE__ is equal to)
        store = json.loads(json_str)#Converts the JSON string into a Python dictionary. NOTE: This creates a nested dictionary, where the ID we need is the outer key and the inner stuff includes the type, legacy ID, etc.
        graphql_id = next(key for key in store.keys() if store[key].get('__typename') == 'Teacher')#next goes through an iterable object one by one. Since it's only called once here, it prints the first object. The loop creates a list, loops through each key in the outer dictionary, checks the value of the __typename entry (if existent), and if it's Teacher then we know this specific inner dictionary (and its outer key, which is the ID) is the one we want. Thus, add that key to the list

        #Put the rating and name of the prof into the object
        prof.rating = store[graphql_id]['avgRating']
        prof.difficulty = store[graphql_id]['avgDifficulty']
        prof.firstName = store[graphql_id]['firstName']
        prof.lastName = store[graphql_id]['lastName']
        prof.numRatings = store[graphql_id]['numRatings']

        return prof
        
    def getProfReviews(self, prof):
        #Get the HTML from RMP. The header is required because RMP blocks Python bots, so we must pretend to be an actual browser
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(prof.url, headers=headers)
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

            prof.reviews = reviews
            return prof
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
    
    def getAllIds(self, uni, dept=None):
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

        if dept != None:
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

        return schoolId
    
    def getReviewsAndResponse(self, uni, dept, className):
        allURL = self.getAllProfURL(uni, dept)
        allDeptReviews = []

        for i in allURL:
            profWithReviews = self.getProfReviews(i)
            allDeptReviews.append(profWithReviews.reviews)
        
        geminiResponse = self.generateResponse(allDeptReviews, className) 
        return geminiResponse

    def getAvgRating(self, uni, dept):
        allURL = self.getAllProfURL(self, uni, dept)
        rating = 0
        count = 0
        highProf = Professor()#Doing this creates a prof w/ rating 0 with no other attributes
        lowProf = Professor(rating = 5)#Must be a 5 because a 0 would mean no prof can be worse

        for i in allURL:
            profRating = self.getProfRatings(self, i)

            if profRating.rating != 0: #Since a 0 would massively decrease the average just for an unrated prof, which isn't fair
                rating += profRating.rating
                count += 1
            if profRating.rating > highProf.rating and profRating.numRatings >= 10:#If this is the new best prof in the dept
                highProf = profRating
            elif profRating.rating < lowProf.rating and profRating.numRatings >= 10: #If this is the new worst prof in the dept
                lowProf = profRating

        rating = round(rating/count, 1)
        return rating, f"{highProf.firstName} {highProf.lastName}", f"{lowProf.firstName} {lowProf.lastName}", highProf.rating, lowProf.rating

    def getAllDepts(self, uni):
        #Get the HTML from RMP. The header is required because RMP blocks Python bots, so we must pretend to be an actual browser
        headers = {"User-Agent": "Mozilla/5.0"}
        school_id = self.getAllIds(self, uni)
        response = requests.get(f"https://www.ratemyprofessors.com/search/professors/{school_id}?q=*", headers=headers)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        script_tag = soup.find("script", string=re.compile(r"window\.__RELAY_STORE__"))
        script_text = script_tag.string

        #This function extracts just the inner data from the marker. So, from 'window.DATA = {"a": 1, "b": {"c": 2}, "d": 3};', it returns {"a": 1, "b": {"c": 2}, "d": 3}
        def extract_json_after_equals(text, marker):
            start = text.index(marker) + len(marker)
            start = text.index("{", start)
            depth = 0
            i = start
            while i < len(text):
                ch = text[i]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start:i + 1]
                i += 1
            raise ValueError("No matching brace found")#This only occurs if the JSON in the HTML never ends, which should never happen (since RMP functions)

        relay_json = extract_json_after_equals(script_text, "window.__RELAY_STORE__")
        store = json.loads(relay_json)#Creates a python dictionary out of the JSON

        departments_set = set()

        for node in store.values():#Discards the keys in the dictionary; looks just at the values. 
            if isinstance(node, dict) and node.get("__typename") == "FilterOption" and node.get("value"):#If that "node"/value is one of the inner dictionaries, and it's a filter option (since the department names are all filter options) and it has a "value" (the value key corresponds to the dept name)
                if "amp" not in node["value"]:#Sometimes due to parsing errors, the depts with & in their name get duplicated with an amp. This deletes those
                    departments_set.add(node["value"].capitalize())#Add the value coresponding to the value key

        departments = sorted(departments_set)#Sort it alphabetically

        return departments

    def getPlots(self, uni, dept):
        #Build the data
        allProfs = self.getAllProfURL(self, uni, dept)

        for i in allProfs[:]:#The extra : creates a temporary copy of the list to use for the loop
            updatedProf = self.getProfRatings(self, i)#This gets all the data we need and loads it into the object
            allProfs.remove(i)#Remove the object without all the info from the original list

            if updatedProf.numRatings > 10:
                allProfs.append(updatedProf) #If they have 10 reviews, add them back into the real list with all their info

        allRatings = [i.rating for i in allProfs]
        allDifficulties = [i.difficulty for i in allProfs]
        labels = [f"{i.firstName} {i.lastName}: ({i.difficulty}, {i.rating})" for i in allProfs]

        #Build the first chart
        fig, ax = plt.subplots(figsize=(6, 4))
        scatter = ax.scatter(allDifficulties, allRatings, label="Difficulty vs Prof Rating", color="blue", s=30)

        tooltip = mpld3.plugins.PointHTMLTooltip(scatter, labels=labels, hoffset=10, voffset=10)
        mpld3.plugins.connect(fig, tooltip)

        ax.set_title("Prof Rating vs. Difficulty (hover for specifics)", fontsize=12, fontweight="bold")
        ax.set_xlabel("Prof Difficulty (/5)")
        ax.set_ylabel("Prof Rating (/5)")

        html_str1 = mpld3.fig_to_html(fig)
        plt.close(fig)

        #Build the second chart
        bins = [1,2,3,4,5]
        fig, ax = plt.subplots(figsize=(6, 4))
        scatter = ax.hist(allRatings, bins=bins, edgecolor="black")
        plt.xticks(bins)

        ax.set_title("Department Ratings Distribution", fontsize=12, fontweight="bold")
        ax.set_xlabel("Rating Range")
        ax.set_ylabel("Frequency")

        html_str2 = mpld3.fig_to_html(fig)
        plt.close(fig)
        return html_str1, html_str2


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