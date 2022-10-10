from django.contrib.auth.models import User
from rest_framework import serializers

userfields = (
    "id",
    "first_name",
    "last_name",
    "username",
    "email",
    "is_active",
    "is_superuser",
    "is_staff",
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = userfields


class UserInitialsSerializer(serializers.ModelSerializer):
    profile = serializers.SlugRelatedField(read_only=True, slug_field="initials")

    class Meta:
        model = User
        fields = userfields + ("profile",)


def commonfields_postserializer(rowdict, userid):
    cd = {
        "id": rowdict["id"],
        "name": rowdict["name"],
        "ownerid": rowdict["user"]["id"],
        "user": rowdict["user"]["profile"],
        "is_shared": rowdict.get("is_shared", False),
        "created": rowdict["dtm_created"],
        "updated": rowdict["dtm_updated"],
    }

    userperm = None

    sharedwith = []
    for x in rowdict["sharedwith"]:
        if x["authorized"].id == userid:
            userperm = x["perm"].name
        s = {
            "actorid": x["actor"].id,
            "actor": x["actor"].profile.initials,
            "authorizedid": x["authorized"].id,
            "authorized": x["authorized"].profile.initials,
            "permid": x["perm"].id,
            "perm": x["perm"].name,
        }
        sharedwith.append(s)

    cd["permission"] = userperm
    cd["sharedwith"] = sharedwith

    return cd
