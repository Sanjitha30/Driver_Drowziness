import pyttsx3
import datetime
import speech_recognition as sr
import webbrowser
import os
import sys
import pywhatkit
import pyjokes
import requests
import time
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

engine = pyttsx3.init()

def fun_talk(audio):
    engine.say(audio)
    engine.runAndWait()

def wish_user():
    hour = int(datetime.datetime.now().hour)
    if hour >= 0 and hour < 12:
        fun_talk("Good Morning!")
    elif hour >= 12 and hour < 18:
        fun_talk("Good Afternoon!")
    else:
        fun_talk("Good Evening!")
    fun_talk("I am your car assistant. How may I help you?")

def get_command():
    rec = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        rec.pause_threshold = 1
        audio = rec.listen(source)
        try:
            print("Recognizing...")
            query = rec.recognize_google(audio, language='en-in')
            print(f"User said: {query}\n")
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
            return "None"
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return "None"
        except Exception as e:
            print(e)
            print("Say that again please...")
            return "None"
        return query

def get_weather(city):
    api = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid=eea37893e6d01d234eca31616e48c631"
    w_data = requests.get(api).json()
    weather = w_data['weather'][0]['main']
    temp = int(w_data['main']['temp'] - 273.15)
    temp_min = int(w_data['main']['temp_min'] - 273.15)
    temp_max = int(w_data['main']['temp_max'] - 273.15)
    pressure = w_data['main']['pressure']
    humidity = w_data['main']['humidity']
    visibility = w_data['visibility']
    wind = w_data['wind']['speed']
    sunrise = time.strftime("%H:%M:%S", time.gmtime(w_data['sys']['sunrise'] + 19800))
    sunset = time.strftime("%H:%M:%S", time.gmtime(w_data['sys']['sunset'] + 19800))

    all_data1 = f"Condition: {weather} \nTemperature: {temp}°C\n"
    all_data2 = f"Minimum Temperature: {temp_min}°C \nMaximum Temperature: {temp_max}°C \nPressure: {pressure} millibar \nHumidity: {humidity}% \nVisibility: {visibility} metres \nWind: {wind} km/hr \nSunrise: {sunrise}  \nSunset: {sunset}"
    return all_data1, all_data2

def get_distance(location1, location2):
    geocoder = Nominatim(user_agent="car_assistant")
    coordinates1 = geocoder.geocode(location1)
    coordinates2 = geocoder.geocode(location2)

    lat1, long1 = coordinates1.latitude, coordinates1.longitude
    lat2, long2 = coordinates2.latitude, coordinates2.longitude

    place1 = (lat1, long1)
    place2 = (lat2, long2)

    distance_places = geodesic(place1, place2).kilometers
    return distance_places

if __name__ == '__main__':
    wish_user()
    while True:
        query = get_command().lower()

        if 'open youtube' in query:
            fun_talk("Opening YouTube")
            webbrowser.open("www.youtube.com")

        elif 'play' in query:
            cmd_info = query.replace('play', '')
            fun_talk(f'Playing {cmd_info}')
            pywhatkit.playonyt(cmd_info)

        elif 'the time' in query:
            strTime = datetime.datetime.now().strftime("%H:%M:%S")
            fun_talk(f"The time is {strTime}")

        elif 'the date' in query:
            strDate = datetime.datetime.today().strftime('%Y-%m-%d')
            fun_talk(f"The date is {strDate}")

        elif 'weather' in query or 'temperature' in query:
            fun_talk("Tell me the city name.")
            city = get_command()
            if city != "None":
                try:
                    all_data1, all_data2 = get_weather(city)
                    fun_talk(f"Gathering the weather information of {city}...")
                    fun_talk(all_data1)
                    fun_talk(all_data2)
                except Exception as e:
                    fun_talk("Sorry, I couldn't retrieve the weather information.")
                    print(f"Error: {e}")

        elif 'distance' in query:
            fun_talk("Tell me the first city name.")
            location1 = get_command()
            fun_talk("Tell me the second city name.")
            location2 = get_command()
            if location1 != "None" and location2 != "None":
                try:
                    distance_places = get_distance(location1, location2)
                    fun_talk(f"The distance between {location1} and {location2} is {distance_places:.2f} kilometers.")
                except Exception as e:
                    fun_talk("Sorry, I couldn't calculate the distance.")
                    print(f"Error: {e}")

        elif 'joke' in query:
            joke = pyjokes.get_joke()
            fun_talk(joke)

        elif 'exit' in query:
            fun_talk("Exiting. Have a safe drive!")
            sys.exit()
