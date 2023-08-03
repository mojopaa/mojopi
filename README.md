# Mojo Package Index

### Installation and Usage

以下步驟會 clone 兩個專案，並安裝到同一個 `.venv`

- Use `pip install pdm`

- `git clone git@github.com:drunkwcodes/mojopi.git`
- `git clone git@github.com:drunkwcodes/mups.git`
- `cd mojopi`
- `pdm install -d`
- `cd ../mups`
- `pdm use -f /path/to/mojopi/.venv`
- `pdm install`

- activate venv

    Windows:
    `.venv\Scripts\activate`

    Linux:
    `.venv/bin/activate`

- `python src/mojopi/admin.py` to start server with admin mode.
- Open web browser, open 127.0.0.1:5000

### Screenshots

1. Index Page

![](screenshots/first_page.png)

2. Search Result

![](screenshots/search_result.png)

3. Project Page

![](screenshots/project_landing_page.png)

4. Project Releases

![](screenshots/releases.png)

5. Project Downloads

![](screenshots/downloads.png)

6. Login Page

![](screenshots/login.png)

7. Profile

![](screenshots/profile_page.png)


### Contruibuting

Please see [CONTRIBUTING](CONTRIBUTING.md)

**Seeking experienced Materializecss frontend developers!**
There are quite a lot of UIs to be tweaked. The TODOs are in the [TODO.md](TODO.md)