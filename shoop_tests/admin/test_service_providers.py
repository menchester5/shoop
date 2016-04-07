# -*- coding: utf-8 -*-
# This file is part of Shoop.
#
# Copyright (c) 2012-2016, Shoop Ltd. All rights reserved.
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.

import pytest

from bs4 import BeautifulSoup
from django.test import override_settings

from shoop.admin.modules.service_providers.views import ServiceProviderEditView
from shoop.apps.provides import override_provides
from shoop.core.models import CustomCarrier, CustomPaymentProcessor
from shoop.testing._pseudo_payment import PseudoPaymentProcessor
from shoop.testing.factories import get_default_shop
from shoop.testing.utils import apply_request_middleware


def get_bs_object_for_view(request, view, user, object=None):
    """
    Help function to get BeautifulSoup object from the html rendered
    by the edit view.

    Also override ``service_provider_admin_forms`` here to enable
    ``PseudoPaymentProcessor``
    """
    with override_provides("service_provider_admin_forms", [
        "shoop.testing._pseudo_payment.PseudoPaymentProcessorForm",
        "shoop.admin.modules.service_providers.forms:CustomCarrierForm",
        "shoop.admin.modules.service_providers.forms:CustomPaymentProcessorForm"
    ]):
        request = apply_request_middleware(request, user=user)
        response = view(request, pk=object.pk if object else None)
        if hasattr(response, "render"):
            response.render()
        assert response.status_code in [200, 302]
        return BeautifulSoup(response.content)


@pytest.mark.parametrize("sp_model,type_param", [
    (None, None),
    (CustomCarrier, "CustomCarrier"),
    (CustomPaymentProcessor, "CustomPaymentProcessor")
])
def test_new_service_providers_type_select(rf, admin_user, sp_model, type_param):
    """
    Test `ServiceProvideEditView`` with different types of
    ``ServiceProvider`` subclasses. Make sure that view is rendered
    and creating new object works.

    To make things little bit more simple let's use only english as
    an language.
    """
    with override_settings(LANGUAGES=[("en", "en")]):
        shop = get_default_shop()
        view = ServiceProviderEditView.as_view()
        url = "/"
        if type_param:
            url += "?type=%s" % type_param
        soup = get_bs_object_for_view(rf.get(url), view, admin_user)
        selected_type = soup.find("select", attrs={"id": "id_type"}).find("option", selected=True)["value"]
        if type_param:
            assert type_param == selected_type
        else:
            assert selected_type in ["CustomCarrier", "CustomPaymentProcessor", "PseudoPaymentProcessor"]

        if sp_model:
            name = "Some provider"
            data = {
                "name__en": name,
                "enabled": True,
                "shop": shop.pk,
            }
            assert sp_model.objects.count() == 0
            get_bs_object_for_view(rf.post(url, data=data), view, admin_user)
            assert sp_model.objects.count() == 1
            assert sp_model.objects.first().name == name


def test_invalid_service_provider_type(rf, admin_user):
    """
    Test `ServiceProvideEditView`` raises when used in with wrong
    type parameter.
    """
    get_default_shop()
    view = ServiceProviderEditView.as_view()
    url ="/?type=SomethingThatIsNotProvided"

    with pytest.raises(AttributeError):
        get_bs_object_for_view(rf.get(url), view, admin_user)


@pytest.mark.parametrize("type,extra_inputs", [
    ("CustomPaymentProcessor", []),
    ("PseudoPaymentProcessor", ["bg_color", "fg_color"])
])
def test_new_service_provider_form_fields(rf, admin_user, type, extra_inputs):
    """
    Test `ServiceProvideEditView`` fields in new mode. Based on type
    different input-fields should be visible.

    To make things little bit more simple let's use only english as
    an language.
    """
    with override_settings(LANGUAGES=[("en", "en")]):
        base_inputs = ["name__en", "enabled"]
        get_default_shop()
        view = ServiceProviderEditView.as_view()
        soup = get_bs_object_for_view(rf.get("?type=%s" % type), view, admin_user)
        provider_form = soup.find("form", attrs={"id": "service_provider_form"})
        rendered_fields = []
        for input_field in provider_form.findAll("input"):
            rendered_fields.append(input_field["name"])

        assert rendered_fields == (base_inputs + extra_inputs)


@pytest.mark.parametrize("sp_model,extra_inputs", [
    (CustomCarrier, []),
    (CustomPaymentProcessor, []),
    (PseudoPaymentProcessor, ["bg_color", "fg_color"])
])
def test_service_provide_edit_view(rf, admin_user, sp_model, extra_inputs):
    """
    Test that ``ServiceProvideEditView`` works with existing
    ``ServiceProvider`` subclasses

    To make things little bit more simple let's use only english as
    an language.
    """
    with override_settings(LANGUAGES=[("en", "en")]):
        base_inputs = ["name__en", "enabled"]
        shop = get_default_shop()
        view = ServiceProviderEditView.as_view()
        provider_name = "some name"
        service_provider = sp_model.objects.create(shop=shop, name=provider_name)
        soup = get_bs_object_for_view(rf.get("/"), view, admin_user, object=service_provider)
        provider_form = soup.find("form", attrs={"id": "service_provider_form"})
        rendered_fields = []
        for input_field in provider_form.findAll("input"):
            rendered_fields.append(input_field["name"])

        assert rendered_fields == (base_inputs + extra_inputs)
        assert provider_form.find("input", attrs={"name": "name__en"})["value"] == provider_name