import bs4

class NoaaParser(object):

    def __replace_breaks(self, element):
        for br_el in element.find_all('br'):
                br_el.replace_with(' ')

        return element

    def __safe_int(self, value):
        try:
            return int(value)
        except ValueError:
            return None

    def __safe_float(self, value):
        try:
            return float(value)
        except ValueError:
            return None

    def _parse_location(self, soup):
        div_el = soup.find('div', id='current-conditions')
        location, identifier = div_el.find('h2', class_='panel-title').text.rsplit(' ', 1)
        identifier = identifier[1:-1]
        elevation = self.__safe_int(div_el.find('span', class_='smallTxt').text.split('\xa0')[-1].replace('ft.', ''))

        return {
            'name': location,
            'identifier': identifier,
            'elevation': elevation,
        }

    def _parse_conditions_summary(self, soup):
        div_el = soup.find('div', id='current_conditions-summary')
        p_els = div_el.find_all('p')

        return {
            'icon': f'https://forecast.weather.gov/{div_el.find("img").get("src")}',
            'conditions': p_els[0].text.strip(),
            'temp_f': self.__safe_int(p_els[1].text.replace('°F', '')),
        }

    def _parse_conditions_details(self, soup):
        div_el = soup.find('div', id='current_conditions_detail')
        table_el = div_el.find('table')
        tr_els = table_el.find_all('tr')

        humidity_pct = self.__safe_int(tr_els[0].find_all('td')[-1].text.replace('%', ''))
        wind_dir = tr_els[1].find_all('td')[-1].text.split(' ')[0]
        wind_sp_mph = self.__safe_int(tr_els[1].find_all('td')[-1].text.split(' ')[1])
        pressure_in = self.__safe_float(tr_els[2].find_all('td')[-1].text.split(' in (')[0])
        pressure_mb = self.__safe_float(tr_els[2].find_all('td')[-1].text.split(' in (')[-1].replace(' mb)', ''))
        dewpoint_f = self.__safe_int(tr_els[3].find_all('td')[-1].text.split('°F')[0])
        visibility_mi = self.__safe_float(tr_els[4].find_all('td')[-1].text.split(' mi')[0])
        wind_chill_f = self.__safe_int(tr_els[5].find_all('td')[-1].text.split('°F')[0])

        return {
            'humidity_pct': humidity_pct,
            'wind_dir': wind_dir,
            'wind_sp_mph': wind_sp_mph,
            'pressure_in': pressure_in,
            'pressure_mb': pressure_mb,
            'dewpoint_f': dewpoint_f,
            'visibility_mi': visibility_mi,
            'wind_chill_f': wind_chill_f,
        }

    def _parse_alerts(self, soup):
        div_el = soup.find('div', class_='panel-danger')
        dangers = []

        if div_el is not None:
            for a_el in div_el.find_all('a'):
                dangers.append({
                    'name': a_el.text.strip(),
                    'href': f'https://forecast.weather.gov/{a_el.get("href")}',
                })

        return dangers

    def _parse_tombstone_forecasts(self, soup):
        forecasts = []

        for li_el in soup.find_all('li', class_='forecast-tombstone'):

            # Replace <br/> tags with spaces
            desc_el = self.__replace_breaks(li_el.find('p', class_='short-desc'))
            period_el = self.__replace_breaks(li_el.find('p', class_='period-name'))

            # Replace double spaces
            desc_long = li_el.find('img').get('alt').replace('  ', ' ').strip()

            # Remove the period name from the beginning
            desc_long = desc_long.split(': ')[-1]

            # Parse the high/low label and value
            hi_lo_text = li_el.find('p', class_='temp').text
            hi_lo_label = hi_lo_text.split(':')[0].strip()
            hi_lo_temp_f = self.__safe_int(hi_lo_text.split(' ')[1])
            hi_lo_type = 'hi' if hi_lo_label == 'High' else 'lo'

            forecasts.append({
                'period': period_el.text.strip(),
                'desc_short': desc_el.text.strip(),
                'hi_lo_temp_f': hi_lo_temp_f,
                'hi_lo_label': hi_lo_label,
                'hi_lo_type': hi_lo_type,
                'icon': f'https://forecast.weather.gov/{li_el.find("img").get("src")}',
                'desc_long': desc_long,
            })

        return forecasts

    def _parse_radar_satellite(self, soup):
        div_el = soup.find('div', id='radar')
        img_els = div_el.find_all('img')
        a_els = div_el.find_all('a')

        return {
            'radar': {
                'href': f'https:{a_els[0].get("href")}',
                'icon': f'https:{a_els[0].find("img").get("src")}',
            },
            'satellite': {
                'href': f'https:{a_els[1].get("href")}',
                'icon': a_els[1].find('img').get('src'),
            }
        }


    def _parse_about(self, soup):
        div_el = soup.find('div', id='about_forecast')
        div_row_els = div_el.find_all('div', class_='fullRow')

        point_fct = self.__replace_breaks(div_row_els[0].find('div', class_='right'))
        point_fct_loc, point_fct_geo = point_fct.text.split(' \xa0')

        return {
            'location': point_fct_loc,
            'geo': point_fct_geo,
            'title': f'7-Day Forecast for {point_fct_geo}',
        }


    def parse(self, html):
        soup = bs4.BeautifulSoup(html, 'html.parser')

        location = self._parse_location(soup)
        summary = self._parse_conditions_summary(soup)
        details = self._parse_conditions_details(soup)
        forecasts = self._parse_tombstone_forecasts(soup)
        rad_sat = self._parse_radar_satellite(soup)
        alerts = self._parse_alerts(soup)
        about = self._parse_about(soup)

        return {
            'conditions': {**summary, **details},
            'forecasts': forecasts,
            'location': location,
            'radar': rad_sat.get('radar'),
            'satellite': rad_sat.get('satellite'),
            'alerts': alerts,
            'about': about,
        }

if __name__ == '__main__':

    import json
    import pathlib
    import requests

    parser = NoaaParser()
    response = requests.get('https://forecast.weather.gov/MapClick.php?lat=39.6121&lon=-104.6745')
    data = parser.parse(response.text)

    pathlib.Path('temp/noaa.json').write_text(json.dumps(data, indent=2))
