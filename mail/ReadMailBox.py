import requests
from fastapi import FastAPI

class ReadMailBox:
    def __init__(self,clientiD,refresh_token,targetmail):
        self.clientID = clientiD
        self.refresh_token = refresh_token 
        self.targetmail = targetmail

    def GetAccessToken(self):
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {
            "client_id": self.clientID,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": "https://graph.microsoft.com/.default",
        }
        response = requests.post(token_url, data=data)
        access_token = response.json().get("access_token")
        return access_token

# FastAPI app
app = FastAPI()
