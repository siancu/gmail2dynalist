The aim of this project is to add mails from GMail to the Inbox in Dynalist.

You need to obtain the credentials for accessing the Google GMail API. This is explained [here](https://developers.google.com/gmail/api/quickstart/python).

To run the script first create a new virtualenv in the project folder:

```shell script
python3 -m venv .
```

Then install the libraries needed for accessing the GMail API:

```shell script
pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```
You need to obtain an API secret from the [Dynalist Developers page](https://dynalist.io/developer). Once you have it, save it in a file called `dynalistToken.txt` in the project root folder.

By default, the script adds only the starred emails to Dynalist. 