import re

import pandas as pd

from cowidev.utils.clean import clean_count, clean_date
from cowidev.utils.gdrive import GSheetApi
from cowidev.vax.utils.incremental import enrich_data, increment


class Colombia:
    location = "Colombia"
    source_url = "https://docs.google.com/spreadsheets/d/1eblBeozGn1soDGXbOIicwyEDkUqNMzzpJoAKw84TTA4"
    gsheets_api = GSheetApi()

    @property
    def sheet_id(self):
        return self.source_url.split("/")[-1]

    def read(self) -> pd.Series:
        ws = self.gsheets_api.get_worksheet(self.sheet_id, "Reporte diario")
        df = self._parse_data(ws)
        return df

    def _parse_data(self, worksheet):
        for row in worksheet.values():
            for value in row:
                if "Total dosis aplicadas" in str(value):
                    total_vaccinations = row[-1]
                    if type(total_vaccinations) != int:
                        total_vaccinations = clean_count(total_vaccinations)
                    date_raw = row[-2]
                    date_str = clean_date(date_raw, "Total dosis aplicadas al %d-%m-%Y")
                elif value == "Total dosis segundas dosis acumuladas":
                    second_doses = row[-1]
                    if type(second_doses) != int:
                        second_doses = clean_count(second_doses)
                elif value == "Total únicas dosis acumuladas":
                    unique_doses = row[-1]
                    if type(unique_doses) != int:
                        unique_doses = clean_count(unique_doses)
                elif value == "Aplicación Refuerzos":
                    boosters = row[-1]
                    if type(boosters) != int:
                        boosters = clean_count(boosters)                    
        first_doses = total_vaccinations - second_doses - unique_doses - boosters
        people_vaccinated = first_doses + unique_doses
        people_fully_vaccinated = second_doses + unique_doses
        total_boosters = boosters

        if total_vaccinations is None or second_doses is None or unique_doses is None:
            raise ValueError("Date is not where it is expected be! Check worksheet")
        return pd.Series(
            {
                "date": date_str,
                "total_vaccinations": total_vaccinations,
                "people_fully_vaccinated": people_fully_vaccinated,
                "people_vaccinated": people_vaccinated,
                "total_boosters": total_boosters,
            }
        )

    def pipe_location(self, ds: pd.Series) -> pd.Series:
        return enrich_data(ds, "location", "Colombia")

    def pipe_vaccine(self, ds: pd.Series) -> pd.Series:
        return enrich_data(ds, "vaccine", "Johnson&Johnson, Moderna, Oxford/AstraZeneca, Pfizer/BioNTech, Sinovac")

    def pipe_source(self, ds: pd.Series) -> pd.Series:
        return enrich_data(ds, "source_url", self.source_url)

    def pipeline(self, ds: pd.Series) -> pd.Series:
        return ds.pipe(self.pipe_location).pipe(self.pipe_vaccine).pipe(self.pipe_source)

    def export(self):
        data = self.read()
        if "total_vaccinations" in data:
            data = data.pipe(self.pipeline)
            increment(
                location=data["location"],
                total_vaccinations=data["total_vaccinations"],
                people_vaccinated=data["people_vaccinated"],
                people_fully_vaccinated=data["people_fully_vaccinated"],
                total_boosters=data["total_boosters"],
                date=data["date"],
                source_url=data["source_url"],
                vaccine=data["vaccine"],
            )
        else:
            print("skipped")


def main():
    Colombia().export()
