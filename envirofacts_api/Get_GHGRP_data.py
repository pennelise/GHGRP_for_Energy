# -*- coding: utf-8 -*-
"""
Original code by @calmc, colin.mcmillan@nrel.gov (2020-08-12)
Refactored by @pennelise, epenn@g.harvard.edu (2023-05-08)
"""
#
import pandas as pd
import numpy as np
import requests
from typing import Optional


class GHGRP_API:
    """
    Access GHGRP data through Envirofacts API.
    The query should work for most tables associated with GHGRP, but only the
    following tables have been tested:
        - All of section FF (coal)
        - C_FUEL_LEVEL_INFORMATION
        - D_FUEL_LEVEL_INFORMATION
        - c_configuration_level_info
        - V_GHG_EMITTER_FACILITIES
    For a full list of available tables see:
        https://www.epa.gov/enviro/greenhouse-gas-model
    For detailed documentation on the API see:
        https://www.epa.gov/enviro/web-services#table

    Example
    -------
    Here's an example application for downloading emitter facility information
    from table V_GHG_EMITTER_FACILITIES for the 2018 reporting year::

        from Get_GHGRP_data import GHGRP_API
        emitter_facility_info = GHGRP_API().get_data(
            table='V_GHG_EMITTER_FACILITIES', reporting_year=2018)

    """

    BASE_URL = "https://enviro.epa.gov/enviro/efservice/"

    @staticmethod
    def read_path(path: str) -> pd.DataFrame:
        """Read a CSV file from a URL."""
        assert requests.get(path).status_code == 200, "URL does not exist."
        return pd.read_csv(path, low_memory=False)

    def get_table_slice(
        self,
        table: str,
        start_row: int,
        end_row: int,
        custom_query: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Query a slice of a table from the EPA API.

        Parameters
        ----------
        table: str
            Name of the GHGRP Envirofacts table to query.
        start_row: int
            First row to query.
        end_row: int
            Last row to query.
        custom_query: str, optional
            Custom query to add to the URL. See
            https://www.epa.gov/enviro/web-services#table
            for detailed documentation on the API. Custom queries are steps 2, 3, and 4
            in the "Constructing a Search" section of the documentation.

        Returns
        -------
        ghgrp_data:
            Dataframe of the queried table.
        """
        custom_query = custom_query or ""
        path = f"{self.BASE_URL}/{table}/{custom_query}/rows/{start_row}:{end_row}/csv"
        return self.read_path(path)

    def get_row_count(self, table: str, custom_query: Optional[str] = None) -> int:
        """Get the number of rows in a table."""
        custom_query = custom_query or ""
        path = f"{self.BASE_URL}/{table}/{custom_query}/count/csv"
        df = self.read_path(path)
        if "TOTALQUERYRESULTS" in df.columns:
            count = int(df["TOTALQUERYRESULTS"].values[0])
        elif df.empty:  # some tables return only the count, with no column name
            count = int(df.columns.values[0])
        else:
            raise ValueError("Count file format not recognized.")
        return count

    def get_reporting_year_query(
        self, table: str, reporting_year: Optional[int] = None
    ) -> str:
        """Construct a custom_query to select a specific reporting year."""
        if reporting_year is None:
            return ""
        else:
            path = f"{self.BASE_URL}/{table}/rows/0:1/csv"
            df = self.read_path(path)
            # EPA API has different column names for reporting year in different tables
            if "reporting_year" in df.columns.str.lower():
                reporting_year_query = f"reporting_year/{reporting_year}"
            elif "year" in df.columns.str.lower():
                reporting_year_query = f"year/{reporting_year}"
            else:
                raise ValueError("Column name for reporting year not recognized.")
            return reporting_year_query

    def get_data(
        self,
        table: str,
        reporting_year: Optional[int] = None,
        rows: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Query a table from the EPA API, 10,000 rows at a time.

        Parameters
        ----------
        table: str
            Name of the GHGRP Envirofacts table to access.
        reporting_year: int, optional
            Year of data to download. Default value is None, which will download
            all years of data.
        rows: int, optional
            Number of rows to download. Defaults value is None, which will download
            all rows of the table.

        Returns
        -------
        ghgrp_data:
            Dataframe of the queried table.
        """
        reporting_year_query = self.get_reporting_year_query(
            table=table, reporting_year=reporting_year
        )
        max_row = rows or self.get_row_count(
            table=table, custom_query=reporting_year_query
        )

        # slice into 10,000 row chunks because the EPA API has a limit of 10,000 rows
        row_range_without_max = np.arange(start=0, stop=max_row, step=10000, dtype=int)
        row_range = np.append(
            row_range_without_max, max_row
        )  # append last row because np.arange does not include stop

        ghgrp_data = []
        for n in range(len(row_range) - 1):
            table_slice = self.get_table_slice(
                table=table,
                start_row=row_range[n],
                end_row=row_range[n + 1],
                custom_query=reporting_year_query,
            )
            ghgrp_data.append(table_slice)
        ghgrp_data = pd.concat(ghgrp_data)

        ghgrp_data.drop_duplicates(inplace=True)

        return ghgrp_data
