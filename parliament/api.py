from rest_framework import serializers, viewsets

from parliament.models import Parliament, ParliamentMember, PartyMember, PoliticalParty


class ParliamentSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Parliament
        fields = ('id', 'name', 'wikidata_id')


class ParliamentMemberSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ParliamentMember
        fields = ('id', 'person', 'parliament', 'joined', 'left')


class PoliticalPartySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PoliticalParty
        fields = (
            'id',
            'name',
            'name_short',
            'founded',
            'dissolved',
            'wikidata_id',
            'wikimedia_logo_url',
            'wikipedia_url',
            'official_website_url',
        )


class PartyMemberSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PartyMember
        fields = ('id', 'person', 'party', 'joined', 'left')


class ParliamentViewSet(viewsets.ModelViewSet):
    queryset = Parliament.objects.all()
    serializer_class = ParliamentSerializer


class ParliamentMemberViewSet(viewsets.ModelViewSet):
    queryset = ParliamentMember.objects.all()
    serializer_class = ParliamentMemberSerializer


class PoliticalPartyViewSet(viewsets.ModelViewSet):
    queryset = PoliticalParty.objects.all()
    serializer_class = PoliticalPartySerializer


class PartyMemberViewSet(viewsets.ModelViewSet):
    queryset = PartyMember.objects.all()
    serializer_class = PartyMemberSerializer
