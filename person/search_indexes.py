# -*- coding: utf-8 -*-
"""
Created on Tue Apr 11 19:30:38 2017

@author: stef
"""

import datetime
from haystack import indexes
from person.models import Person


class PersonIndex(indexes.SearchIndex, indexes.Indexable):
    forename = indexes.CharField(model_attr='forename')
    surname_prefix = indexes.CharField(model_attr='surname_prefix')
    surname = indexes.CharField(model_attr='surname')
    text = indexes.CharField(use_template=True,document=True)
   
    slug = indexes.CharField(model_attr='slug')
    #birthdate = indexes.DateTimeField(model_attr='birthdate')

    def get_model(self):
        return Person

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()