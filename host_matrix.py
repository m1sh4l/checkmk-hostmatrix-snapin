#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Andy Dustin - License: GNU General Public License v2

## This Host Matrix snapin was dropped from CheckMK in v2.1.0b1 https://checkmk.com/werk/13736, 
## https://github.com/tribe29/checkmk/commit/0bd1c5acc37c5676cc11f48ec760ebcf940a5773. 
## But I still want to use this snapin, so I have taken the last existing version from the 
## 2.0.0 branch and updated it to (hopefully) work with v2.1.0.

import cmk.gui.sites as sites
import cmk.gui.visuals as visuals
from cmk.gui.i18n import _
from cmk.gui.htmllib.html import html
from cmk.gui.plugins.sidebar.utils import (
    CustomizableSidebarSnapin,
    snapin_registry,
    snapin_width,
)
from cmk.gui.utils.urls import urlencode

# This base class is only used by HostMatrixVisualization so far
# TODO: Implement a ServiceMatrixVisualization class
class MatrixVisualization:
    @classmethod
    def livestatus_table(cls):
        return NotImplementedError

    @classmethod
    def livestatus_columns(cls):
        return NotImplementedError

    @classmethod
    def filter_infos(cls):
        return NotImplementedError

    def show(self, width, context):
        return NotImplementedError

    def _get_livestatus(self, context):
        context_filters, only_sites = visuals.get_filter_headers(table=self.livestatus_table(),
                                                                 infos=self.filter_infos(),
                                                                 context=context)
        return self._execute_query(self._get_query(context_filters), only_sites)

    def _execute_query(self, query, only_sites):
        try:
            sites.live().set_prepend_site(True)
            if only_sites:
                sites.live().set_only_sites(only_sites)
            return sites.live().query(query)
        finally:
            sites.live().set_only_sites(None)
            sites.live().set_prepend_site(False)

    def _get_query(self, context_filters):
        query = ("GET %s\n"
                 "Columns: %s\n"
                 "Limit: 901\n" %
                 (self.livestatus_table(), self.livestatus_columns())) + context_filters
        return query


class HostMatrixVisualization(MatrixVisualization):
    @classmethod
    def livestatus_table(cls):
        return "hosts"

    @classmethod
    def livestatus_columns(cls):
        return "name state has_been_checked worst_service_state scheduled_downtime_depth"

    @classmethod
    def filter_infos(cls):
        return ["host"]

    def show(self, width, context):
        hosts = self._get_livestatus(context)
        num_hosts = len(hosts)

        if num_hosts > 900:
            html.write_text(_("Sorry, I will not display more than 900 hosts."))
            return

        # Choose smallest square number large enough
        # to show all hosts
        n = 1
        while n * n < num_hosts:
            n += 1

        rows = int(num_hosts / n)
        lastcols = num_hosts % n
        if lastcols > 0:
            rows += 1

        # Calculate cell size (Automatic sizing with 100% does not work here)
        # This is not a 100% solution but way better than having no links
        cell_spacing = 3
        cell_size = (width - cell_spacing * n) / n
        cell_height = 2 * cell_size / 3

        # Add one cell_spacing so that the cells fill the whole snapin width.
        # The spacing of the last cell overflows on the right.
        html.open_table(class_=["hostmatrix"], style=['width:%spx' % (width + cell_spacing)])
        col, row = 1, 1
        for site, host, state, has_been_checked, worstsvc, downtimedepth in sorted(hosts):
            if col == 1:
                html.open_tr()

            if downtimedepth > 0:
                s = "d"
            elif not has_been_checked:
                s = "p"
            elif worstsvc == 2 or state == 1:
                s = "2"
            elif worstsvc == 3 or state == 2:
                s = "3"
            elif worstsvc == 1:
                s = "1"
            else:
                s = "0"
            url = "view.py?view_name=host&site=%s&host=%s" % (urlencode(site),
                                                              urlencode(host))
            html.open_td(style=[
                "width:%.2fpx" % (cell_size + cell_spacing),
                "height:%.2fpx" % (cell_height + cell_spacing)
            ])
            html.a('',
                   href=url,
                   title=host,
                   target="main",
                   class_=["state", "state%s" % s],
                   style=["width:%.2fpx;" % cell_size,
                          "height:%.2fpx;" % cell_height])
            html.close_td()

            if col == n or (row == rows and n == lastcols):
                html.open_tr()
                col = 1
                row += 1
            else:
                col += 1
        html.close_table()


@snapin_registry.register
class HostMatrixSnapin(CustomizableSidebarSnapin):
    @staticmethod
    def type_name():
        return "hostmatrix"

    @classmethod
    def title(cls):
        return _("Host matrix")

    @classmethod
    def description(cls):
        return _("A matrix showing a colored square for each host")

    @classmethod
    def refresh_regularly(cls):
        return True

    @classmethod
    def vs_parameters(cls):
        return [
            ("context", visuals.VisualFilterList(
                title=_("Filters"),
                info_list=["host"],
            )),
        ]

    @classmethod
    def parameters(cls):
        return {
            "context": {},
        }

    def show(self):
        HostMatrixVisualization().show(snapin_width, self.parameters()["context"])

    @classmethod
    def allowed_roles(cls):
        return ["user", "admin", "guest"]
