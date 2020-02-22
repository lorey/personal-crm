### Import Linkedin
[Linkedin export contacts](https://www.linkedin.com/psettings/member-data)
### Set up PyCharm
To set up a remote interpreter for PyCharm, choose docker-compose, the `web` service.
As a python path, use the return of the following command:
```
docker-compose exec web pipenv --py
```
which should be
```
/root/.local/share/virtualenvs/code-_Py8Si6I/bin/python
```

## ToDo
* Improve import by editing afterwards
* Improve import by extracting and using emails
* Merging contacts
