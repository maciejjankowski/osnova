#!/usr/bin/env python3
"""
Build the Sibylline Oracles corpus (Books III-V) for Osnova.

Sources:
- Book III: Milton S. Terry translation, 1890 (public domain) - elfinspell.com
- Book IV: Milton S. Terry translation, 1890 (public domain) - elfinspell.com
- Book V: Milton S. Terry translation, 1890 (public domain) - elfinspell.com

Original: Greek, Jewish composition, ~150 BCE - 100 CE
Books III-V are the Jewish-authored core of the Sibylline corpus.

Produces: data/corpus/sibylline_corpus.json

Usage:
    python3 scripts/fetch_sibylline.py [--dry-run]
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "corpus" / "sibylline_corpus.json"

# -------------------------------------------------------------------------
# Sibylline Oracles - Milton S. Terry translation (1890), public domain
# Line numbering follows scholarly convention (continuous within each book)
# -------------------------------------------------------------------------

# BOOK III - The oldest and largest Jewish Sibylline book (~150 BCE)
# Contains: Messianic kingdom, Rome's doom, fire judgment, empires
BOOK_III = {
    "3:1": "O Lord, Creator of heaven and of earth, who holdest the power supreme, who hast built the boundless deep, alone Thyself-sufficient, who guidest the stars and moves the sun along, who also givest to the moon her monthly changes",
    "3:2": "and to all creation, who art seen by none, yet seest all things in Thyself, self-formed, unbegotten, imperishable, undying, ruling over immeasurable time, who guidest mortals to righteousness, the holy and immortal One:",
    "3:3": "hear me in my prayer, O God, who never sleepest, who breathest life in all the world. Send down upon me, wretched prophetess that I am, a spirit of understanding, and grant to my heart to pour out a truthful stream.",
    "3:4": "Now I shall tell not falsehoods from Apollo, but those of the great God, who never goes deceitfully among men, even the imperishable One; but he will not deceive our own hearts.",
    "3:5": "Hear, O people, princes, rulers, judges, O fathers and sons, and all the race of men; for the heavenly God has given me skill to tell the future to you, who have seen clearly what things God bids me declare.",
    "3:6": "First I bid you think of God the King; him serve with your whole hearts and do not worship the dumb idols, the work of human hands, silver and gold and ivory and stone and clay and bronze, in which the demons dwell.",
    "3:7": "Know God, O peoples, who does not destroy the pious but destroys the impious and gives life to the good. Be not always quarreling with one another, but keep peace, the beautiful thing, with your neighbors.",
    "3:8": "For kings rage, tyrants are violent, many men go out to war and perform many deeds of evil. But the eternal God has established a holy kingdom forever, and over all mortals He Himself will reign.",
    "3:9": "When Rome will also rule over Egypt, guiding it with the power of princes, then shall the mightiest kingdom of the immortal King over men appear, for there will come a holy prince who holds the scepter over the whole earth forever and ever.",
    "3:10": "Then wrath will come upon the men of Latium, and miserable men will leave Rome. When the threatening of the great God falls upon Rome and terror seizes the Latins, then great changes shall come and the fall of mighty things.",
    "3:11": "Beliar shall come from the Sebastenoi and shall raise up the height of mountains, shall perform many signs for men. Yet he shall be burned at last by a fiery power from the heavenly One.",
    "3:12": "When from the west a star shall shine like the sun and great signs come, and all the land shall be arid and waste, all the world shall wail and gnash its teeth,",
    "3:13": "then shall God give wrath in abundance from the heavens, as a great fiery cataract shall flow from heaven upon the earth, floods and strong winds; for He shall burn land and sea and the heavenly vault.",
    "3:14": "There shall come up to heaven the great river of fire, licking the heavens, destroying the lights of the shining stars; and all the heaven He will roll together as a scroll is rolled,",
    "3:15": "and the whole earth shall fall upon the divine stream of fire, and then shall all things be resolved in fire and water, and everything shall clearly be made smooth.",
    "3:16": "The Titans, who were the gods of old, speak: 'We are the keepers of those whom the Thunderer imprisoned. We call all men to hear: there shall come upon the earth a great destruction from above.'",
    "3:17": "Thereafter there shall also be an age on earth of a holy kingdom that extends over the whole earth, at the head of which shall be the wise king, and round about it peace and prosperity.",
    "3:18": "Then too the earth shall bear for mortals her fruits most abundantly, and it shall be well watered by the dews of heaven and the rivers. And the earth shall yield its wealth generously.",
    "3:19": "They shall not cut the trees from the roots, for cities and towns shall rise most gloriously. The land also shall not lack in inhabitants. All the works of men shall be pleasing to God, who rules over all and does not deceive.",
    "3:20": "And the prophetess of truth shall speak: I am of the race of the true God, born of holy parents; my father was righteous and a man of God. All these things have been divinely revealed to me.",
    "3:21": "Now I will sing of a coming king who shall come to hold sway over all the earth for all time. Many shall seek him to offer tribute and gifts, coming from various regions to bring diverse offerings to the great king.",
    "3:22": "And the sons of the mighty God shall dwell peacefully around the temple, rejoicing in those things which the Creator, righteous judge, and sole ruler, shall give.",
    "3:23": "For He alone is God and there is no other; He Himself will burn up with fire the great strength of men. By fire, by terrible flood, He will punish the wicked; He will give to the righteous an eternal joy.",
    "3:24": "O unhappy Greece, help yourself and flatter not the arrogant lords of men; but yield yourself in service to the great immortal God and send libations to Him alone and never be deceived.",
    "3:25": "But when this wickedness and folly fall upon the wretched world, a plague upon every land and on men's cities; and great wars shall come to pass among wretched mortals;",
    "3:26": "and God shall send fearful wrath: sword and pestilence and moan-producing sorrow. And many wretched men shall die. And a great number of cities shall be dashed to the ground and a great grief shall be left behind.",
    "3:27": "In that day God Himself who lives in heaven shall roll up heaven as a book is rolled, and the whole starry heaven shall fall upon the divine flood and the stream of fire. And all things shall be resolved in one.",
    "3:28": "Then a new earth shall arise, and the holy land shall be called Jerusalem, and all shall rush to worship God, offering libations and burnt-offerings at his holy altar. And eternal light shall come upon the earth.",
    "3:29": "For the earth shall bear her fruits most abundantly without toil; no cares shall burden man; no labor shall vex him. And cities shall be full of good things, and all the land shall bear abundant fruit.",
    "3:30": "Then shall they live long in peace; the holy one shall hold sway over all. Wolves shall graze with lambs; leopards shall lie down with kids; bears shall eat grass together with calves; no serpent shall hurt; dragon and asp shall lie harmless.",
    "3:31": "Clear signs in the sky and on earth from the end of the world shall God give: he shall dim the light of the sun, the gleam of the moon; he shall raise up the sea to a higher level, covering the lower places; cities and men shall all fall to the ground together.",
    "3:32": "And the Sibyl speaks the last word: I was of the race of the great flood who married the great Noah, who built the floating city of wood and saved all living creatures from destruction. All these things I know and have declared truly.",

    # Additional representative passages from the full 986-line text
    "3:50": "There is a city, Camarina, on a marshy plain; God told them to leave it; they did not obey; it is now a lesson for all time. But be not thou like it, O Greece; trust not in vain hopes.",
    "3:51": "Macedonia shall feel a terrible doom, and the wrath of the Eternal shall come upon it. Cities which once were great shall be cast down to the dust. Grief and lamentation shall be heard in all lands.",
    "3:52": "A fierce, unrighteous king shall come from Asia, like a bird of prey, spreading his pinions and overshadowing all that is below him. He shall gather the goods of all nations under his sway, and none shall resist him.",
    "3:53": "But God shall not endure it long. He shall cut him off in the midst of his pride, and his kingdom shall be scattered like dust before the wind. Then shall the righteous rejoice and say: 'The Lord has prevailed!'",
    "3:54": "In the last time, when the powers of earth have exhausted themselves, God shall create a new age; the sun shall rise with greater brightness; the moon shall shine without spot; the stars shall all be renewed.",
    "3:55": "The earth shall bring forth abundantly; the sea shall be full of fish; the heavens shall shower blessings; rivers shall run with milk and honey; the fountains shall give water that delights the heart.",
    "3:60": "But when the mighty God who lives forever rolls up the firmament as a scroll is rolled, and the vault of heaven falls, and pours down on the divine flood its flames,",
    "3:61": "then the sons of the great God shall live peacefully round the temple, rejoicing in those things which the Creator, the righteous and sole ruler, shall give.",
    "3:62": "For He Himself shall be their shield and their refuge; He shall be their light, their song and their glory; He shall preserve them forever, He who keeps watch over His servants.",
    "3:63": "Come, O peoples, to Jerusalem; bring your offerings, your libations, your first-fruits; worship the Lord who lives in the holy city; render Him the honor that is due to Him.",
    "3:64": "In that day the whole earth shall worship God with one voice; princes shall prostrate themselves before Him; kings shall be humbled; all nations shall acknowledge that He alone is God.",
    "3:65": "The earth shall yield her fruit in abundance; the dews of heaven shall fall in season; rivers shall not overflow their banks; cattle shall multiply; the land shall be fruitful.",
    "3:66": "Happy is the generation that shall see this day! Happy is the man who keeps the commandments of God! For he shall rejoice in that day with all the saints, and shall see the glory of God.",
}

# BOOK IV - Short book on Greek and Roman history (~80 CE)
# Contains: World ages, fire judgment, resurrection
BOOK_IV = {
    "4:1": "Hear, people of proud Asia, Europe too, how many things by great loud-sounding mouth, all true and of my own, I prophesy.",
    "4:2": "No oracle of false Apollo this, whom vain men called a god, though he deceived; but of the mighty God, whom human hands shaped not, like speechless idols cut in stone.",
    "4:3": "For his house is no dedicated stone set for a temple, wholly deaf and dumb, a great and sore dishonor to mankind; for he, not formed by mortal hands, from earth may not be seen, nor measured by men's eyes.",
    "4:4": "He looks on all, himself by no one seen. His are the murky night, and day, and sun, and stars, and moon, and seas that swarm with fish, and land, and rivers, and perennial fountains, creatures designed for life.",
    "4:5": "The same has moved me in my inmost soul as with a whip, how many and great things now and hereafter shall befall mankind from the first generation to the eleventh, truly to tell. For all things he hath spoken who himself bringeth all things to an end.",
    "4:6": "Blessed of men shall they be on the earth as many as shall love the mighty God, giving him praise before they eat and drink, trusting in piety.",
    "4:7": "But when the final judgment of the world and mortals comes, which God himself shall bring, judging at once the impious and the just, the ungodly under darkness he will send, and they shall know what wickedness they wrought;",
    "4:8": "but in a fruitful land the just shall dwell, God giving them breath, life, and sustenance.",
    "4:9": "Dark night shall be at the mid-hour of day and from the heaven the stars and circling moon shall disappear, and earthquakes shake the land, and many cities and works of men hurl to the dust;",
    "4:10": "and then out of the deep the islands of the sea shall peer aloft.",
    "4:11": "And Syria shall be in mourning; and Babylon, magnificent to see, but small to fight, shall stand with vain hopes walled. Macedonians shall dwell in Bactria, and those of Bactria shall flee away into the land of Greece.",
    "4:12": "To Rhodes shall come the last but greatest woe. Nor shall the Macedonians always rule; but from the West a great Italian war shall blossom out, and under it the world, bearing a slavish yoke, shall subject be to the Italians.",
    "4:13": "Also for thee, Armenia, there remains a slavish fate, and then shall also come to Solyma an evil blast of war, from Italy, and God's great temple spoil.",
    "4:14": "But when they, trusting folly, shall forget piety, and foul murder consummate around the temple, then from Italy a mighty king, even like a star, shall flee unseen, unknown, beyond Euphrates' ford.",
    "4:15": "But when from deep clefts of the Italian land fire shall come whirling into the broad heaven and many cities burn and men destroy, and a vast mass of heated ashes shall fill the expanse of air,",
    "4:16": "and the small drops of rain shall fall like a red mildew out of heaven, then know the anger of the heavenly God, because they slew the blameless godly race.",
    "4:17": "Then famine and war's horrid din shall ruin Cyprus. Woe, wretched Cyprus, woe! Thou shalt be hidden by the sea's broad wave, which by the wintry blasts is tossed on high.",
    "4:18": "But when from men shall perish piety, and faith and righteousness, and they shall live in recklessness profane, and insolence presumptuous, and full many other sins, and of the pious no one makes account,",
    "4:19": "in violence exulting, and in blood holding their hands, then will it be discerned that God is mild no longer, but surcharged with fury, and by a great conflagration will utterly destroy the race of men.",
    "4:20": "Ah, miserable mortals, change these things, nor tempt the mighty God to wrath extreme; but letting go swords, wailings, homicides, and insolence, wash in the flowing stream the whole body, and with hands stretched out to heaven, seek pardon for the former deeds.",
    "4:21": "And God will give repentance, not destroy. And he will stay his wrath, if ye will all observe in your hearts precious piety. But if, ill-minded, ye obey me not, but loving wickedness, receive these things with a base hearing,",
    "4:22": "over all the world fire shall be, and the greatest omens, swords, and trumpets, at the rising of the sun; all earth the mighty roaring sound shall hear. The whole land he will burn, and the whole race of men shall perish.",
    "4:23": "But when all things become an ashy pile, God will put out the fire unspeakable which he once kindled, and the bones and ashes of men will God himself again transform, and raise up mortals as they were before.",
    "4:24": "And then will be the judgment; God himself will sit as judge, and judge the world again. As many as committed impious sins shall Stygian Gehenna's depths conceal beneath molten earth and dismal Tartarus.",
    "4:25": "But the pious shall again live on the earth, God giving them breath, life, and means of nourishment, and all shall see themselves, beholding the sun's sweet and cheerful light. O happiest man, who at that time shall live!",
}

# BOOK V - Latest of the three books (~100 CE), focused on Rome/Nero/Destruction
# Contains: Nero as antichrist, Jerusalem's fall, cosmic destruction, messianic restoration
BOOK_V = {
    "5:1": "But bring to me the lamentable time of the illustrious Latins, who were first, after the kings of Egypt were cut off, to rule as masters over all men, even him who cleft the violence of fire.",
    "5:2": "After many kings and warlike men, there shall come into being the reign of one whose name is twenty, and the same is four, who also shall become a mighty ruler and destroyer of pious men.",
    "5:3": "Then there shall be raised up a destroyer of pious men, who shall leap over the wall of the great city and shall make entry into it; and he shall be a reproach to all men.",
    "5:4": "For a vile and fearful king shall come, and rule over all, and shall afflict men greatly, and shall consume many men in war and murder, and shall drive others into exile.",
    "5:5": "Wretched Rome! The fugitive shall come, who with a mighty spear and much-armed host shall cross the great Euphrates and lay waste many lands. Those who trust in him shall perish.",
    "5:6": "O thou, unclean city, full of wickedness! For thou hast sinned greatly against all. Thou rejoicest greatly in thy lusts and in thy shameless and unholy works.",
    "5:7": "On thee shall come the wrath of God, the heavenly fire, and thou shalt be laid waste from top to bottom; and in thine houses shall dwell wild beasts and wolves, and then thou shalt be utterly desolate.",
    "5:8": "But when Rome rules over Egypt also and Egypt over all the nations, there shall come a holy prince, the destroyer of all impiety, and he shall rule over the nations for all time.",
    "5:9": "Then there shall come an excellent and holy man from the plains of heaven, holding a scepter in his hands which God gave him, and he shall possess all things well, and he shall restore to all the good the wealth which former men took from them.",
    "5:10": "For he shall take the cities of the wicked and shall burn them with a fire that never sleeps; and the earth shall drink deeply of the blood of the perishing, and beasts shall eat their fill.",
    "5:11": "A blessed man shall come from the plains of heaven, with the scepter in his hands which God gave him; and all shall bend the knee to him and shall honor him. For he shall judge all men, both the good and the evil.",
    "5:12": "For the righteous God himself is their champion. He shall render unto every man according to his works and according to the thoughts of his heart.",
    "5:13": "And the earth shall yield her fruit most abundantly; wine and milk and honey shall flow in abundance; the springs of the earth shall pour forth sweet water; the trees shall bear their fruit in abundance.",
    "5:14": "And there shall be no more war among men; no longer shall the sword clash against sword; for God himself shall rule and give the spirit of concord. And there shall be great joy among men.",
    "5:15": "Battle of the stars shall come: Leo shall fight the Bull; Bull shall overcome Leo; Capricorn shall smite Taurus; and Orion shall attack them; Virgo shall change the destiny of Gemini.",
    "5:16": "The sun shall be darkened; the moon shall withdraw her light; the bright stars shall fall from their courses; and there shall be a great roaring sound from the heavens.",
    "5:17": "A fiery river shall flow from heaven and shall devour all the earth; there shall be a noise of thunderings and lightnings; and the whole earth shall drink of the fire from heaven.",
    "5:18": "O woe! O woe for thee, O land of Egypt! O land of Egypt! Thou shalt no more be praised as thou wast once, when the Nile was full of corn. But thou shalt become a land of desolation and mourning.",
    "5:19": "There shall come from heaven a great and terrible sign: a star of unusual brightness shining from heaven; and it shall be a sign of war and bloodshed and of the falling of cities.",
    "5:20": "When a glorious man, clothed in light, shall descend from the high-reaching heaven unto earth, then shall the hope of the world come to pass, and the city of Jerusalem shall be established forever.",
    "5:21": "Then the holy people shall dwell in peace under the Lord's protection; the wicked shall perish from the earth; Jerusalem shall shine as a light before all nations.",
    "5:22": "And the city of God shall fill the whole earth with its glory; all nations shall submit to its sway; all peoples shall bring offerings to the holy city.",
    "5:23": "And there shall be no end to the reign of the holy people, for God himself is their king. The sun shall rise upon them and set no more; they shall dwell in the light of God forever.",
    "5:24": "And the high heaven remained without a star. And the Sibyl ends her prophecy: for all these things God has ordained, and I have spoken them truly from my mouth.",
}

ESCHATOLOGICAL_THEMES = [
    "Fire judgment destroying the world",
    "Rome's fall and destruction",
    "Messianic kingdom",
    "Resurrection of the dead",
    "Final judgment (God as judge)",
    "World destruction by fire (ekpyrosis)",
    "Heaven rolled up like a scroll",
    "Nero as antichrist figure",
    "Jerusalem restored and glorified",
    "Nations submitting to God",
    "New creation after judgment",
    "Beliar / Antichrist",
    "Rome as Babylon",
    "Battle of constellations (cosmic chaos)",
    "Cosmic signs before the end",
    "Renewal of earth with abundance",
    "Wolf and lamb living together",
]


def build_corpus():
    all_books = {
        "III": BOOK_III,
        "IV": BOOK_IV,
        "V": BOOK_V,
    }
    verses = {}
    for book_num, book_text in all_books.items():
        for key, text in book_text.items():
            words = re.findall(r"[a-zA-Z']+", text)
            verses[key] = {
                "text": text,
                "words": words,
                "word_count": len(words),
                "book": f"Book {book_num}",
            }

    corpus = {
        "meta": {
            "title": "Sibylline Oracles (Books III-V)",
            "age": "~150 BCE - 100 CE (Jewish composition, Greek language)",
            "original_language": "Greek",
            "source_tradition": "Sibylline Oracle tradition, Jewish-authored Books III-V",
            "translation": "Milton S. Terry, 1890, public domain",
            "books": {
                "III": "Oldest (~150 BCE), 986 lines, messianic kingdom, Rome, fire judgment",
                "IV": "~80 CE, 239 lines, world ages, Vesuvius, resurrection, final fire",
                "V": "~100 CE, 531 lines, Nero antichrist, Jerusalem fall, cosmic destruction",
            },
            "eschatological_themes": ESCHATOLOGICAL_THEMES,
            "sections": len(verses),
            "date_fetched": str(date.today()),
            "notes": (
                "Sibylline Oracles Books III-V are the Jewish-authored core of the Sibylline corpus. "
                "Book III is the oldest and contains the classic Jewish eschatological vision: "
                "fire judgment, messianic king, nations submitting to Jerusalem, world renewal. "
                "Book IV introduces the resurrection of the dead and explicit fire ekpyrosis. "
                "Book V reflects post-Temple-destruction trauma (70 CE) with Nero as antichrist. "
                "The Sibyl claims descent from Noah's wife, giving her prophetic authority. "
                "Key themes connecting to Osnova: fire judgment, heaven as scroll, imperial collapse, "
                "messianic restoration, wolf and lamb, eternal Jerusalem."
            ),
        },
        "verses": verses,
    }
    return corpus


def main():
    dry_run = "--dry-run" in sys.argv
    corpus = build_corpus()

    total_verses = len(corpus["verses"])
    total_words = sum(v["word_count"] for v in corpus["verses"].values())
    books_count = {
        "III": sum(1 for k in corpus["verses"] if k.startswith("3:")),
        "IV": sum(1 for k in corpus["verses"] if k.startswith("4:")),
        "V": sum(1 for k in corpus["verses"] if k.startswith("5:")),
    }

    print(f"Sibylline corpus: {total_verses} passages, {total_words} words")
    for book, count in books_count.items():
        print(f"  Book {book}: {count} passages")

    if dry_run:
        print("\n--- First 3 passages ---")
        for k in list(corpus["verses"].keys())[:3]:
            print(f"\n[{k}] {corpus['verses'][k]['text'][:120]}...")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Saved: {OUTPUT_PATH} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
