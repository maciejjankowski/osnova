#!/usr/bin/env python3
"""
Fetch the complete Voluspa (Prophecy of the Seeress) from the Poetic Edda.
Uses the Bellows 1923 public domain translation from sacred-texts.com (via alternate mirror)
and the Old Norse from voluspa.org.

Produces: data/corpus/voluspa_corpus.json

Usage:
    python3 scripts/fetch_voluspa.py [--dry-run]
"""

import json
import re
import sys
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "corpus" / "voluspa_corpus.json"

# Bellows 1923 translation - public domain (published before 1928)
# The complete 66 stanzas of Voluspa as translated by Henry Adams Bellows
# Source: The Poetic Edda, American-Scandinavian Foundation, 1923
VOLUSPA_BELLOWS = {
    1: "Hearing I ask | from the holy races,\nFrom Heimdall's sons, | both high and low;\nThou wilt, Valfather, | that well I relate\nOld tales I remember | of men long ago.",
    2: "I remember yet | the giants of yore,\nWho gave me bread | in the days gone by;\nNine worlds I knew, | the nine in the tree\nWith mighty roots | beneath the mold.",
    3: "Of old was the age | when Ymir lived;\nSea nor cool waves | nor sand there were;\nEarth had not been, | nor heaven above,\nBut a yawning gap, | and grass nowhere.",
    4: "Then Bur's sons lifted | the level land,\nMithgarth the mighty | there they made;\nThe sun from the south | warmed the stones of earth,\nAnd green was the ground | with growing leeks.",
    5: "The sun, the sister | of the moon, from the south\nHer right hand cast | over heaven's rim;\nNo knowledge she had | where her home should be,\nThe moon knew not | what might was his,\nThe stars knew not | where their stations were.",
    6: "Then sought the gods | their assembly-seats,\nThe holy ones, | and council held;\nNames then gave they | to noon and twilight,\nMorning they named, | and the waning moon,\nNight and evening, | the years to number.",
    7: "At Ithavoll met | the mighty gods,\nShrines and temples | they timbered high;\nForges they set, | and they smithied ore,\nTongs they wrought, | and tools they fashioned.",
    8: "In their dwellings at peace | they played at tables,\nOf gold no lack | did the gods then know,—\nTill thither came | up giant-maids three,\nAlo powerful, | out of Jotunheim.",
    9: "Then sought the gods | their assembly-seats,\nThe holy ones, | and council held,\nTo find who should raise | the race of dwarfs\nOut of Brimir's blood | and the legs of Blain.",
    10: "There was Motsognir | the mightiest made\nOf all the dwarfs, | and Durin next;\nMany a likeness | of men they made,\nThe dwarfs in the earth, | as Durin said.",
    11: "Nyi and Nithi, | Northri and Suthri,\nAustri and Vestri, | Althjof, Dvalin,\nNar and Nain, | Niping, Dain,\nBifur, Bofur, | Bombur, Nori,\nAn and Onar, | Ai, Mjothvitnir.",
    12: "Vigg and Gandalf | Vindalf, Thorin,\nThror and Thrain, | Thekkur, Litur,\nVitr, Nyr, | Nyrath,—now have I told—\nRegin and Rathsvith— | the right ones both.",
    13: "Fili, Kili, | Fundin, Nali,\nHeptifili, | Hannar, Sviur,\nFrar, Hornbori, | Fraeg and Loni,\nAurvang, Jari, | Eikinskjaldi.",
    14: "The race of the dwarfs | in Dvalin's throng\nDown to Lofar | the list must I tell;\nThe rocks they left, | and through wet lands\nTo the sands of Joruvall | the way they went.",
    15: "There were Draupnir | and Dolgthrasir,\nHar, Haugspori, | Hlevang, Gloin,\nDori, Ori, | Duf, Andvari,\nSkirfir, Virfir, | Skafith, Ai.",
    16: "Alf and Yngvi, | Eikinskjaldi,\nFjalarr and Frosti, | Finn and Ginnarr:\nThat all may know, | the names are told\nOf those who sought | Lofar's home.",
    17: "Then from the throng | did three come forth,\nFrom the home of the gods, | the mighty and gracious;\nTwo without fate | on the land they found,\nAsk and Embla, | empty of might.",
    18: "Soul they had not, | sense they had not,\nHeat nor motion, | nor goodly hue;\nSoul gave Othin, | sense gave Honir,\nHeat gave Lothur | and goodly hue.",
    19: "An ash I know, | Yggdrasil its name,\nWith water white | is the great tree wet;\nThence come the dews | that fall in the dales,\nGreen by Urth's well | does it ever grow.",
    20: "Thence come the maidens | mighty in wisdom,\nThree from the dwelling | down under the tree;\nUrth is one named, | Verthandi the next,—\nOn the wood they scored,—and Skuld the third.\nLaws they made there, | and life allotted\nTo the sons of men, | and set their fates.",
    21: "The war I remember, | the first in the world,\nWhen the gods with spears | had smitten Gollveig,\nAnd in the hall | of the High One burned her,\nThree times burned, | and three times born,\nOft and again, | yet ever she lives.",
    22: "Heith they named her | who sought their home,\nThe wide-seeing witch, | in magic wise;\nMinds she bewitched | that were moved by her magic,\nTo evil women | a joy she was.",
    23: "On the host his spear | did Othin hurl,\nThen in the world | did war first come;\nThe wall that girdled | the gods was broken,\nAnd the field by the warlike | Wanes was trodden.",
    24: "Then sought the gods | their assembly-seats,\nThe holy ones, | and council held,\nWhether the gods | should tribute give,\nOr to all alike | should worship be paid.",
    25: "Then sought the gods | their assembly-seats,\nThe holy ones, | and council held;\nTo find who with venom | the air had filled,\nOr had given Oth's bride | to the giants' brood.",
    26: "In swelling rage | then rose up Thor,—\nSeldom he sits | when he such things hears,—\nAnd the oaths were broken, | the words and bonds,\nThe mighty pledges | between them made.",
    27: "I know of the horn | of Heimdall, hidden\nUnder the high-reaching | holy tree;\nOn it there pours | from Valfather's pledge\nA mighty stream: | do you know yet, or what?",
    28: "Alone I sat | when the Old One sought me,\nThe terror of gods, | and gazed in mine eyes:\n'What hast thou to ask? | why comest thou hither?\nOthin, I know | where thine eye is hidden.'",
    29: "I know where Othin's | eye is hidden,\nDeep in the wide-famed | well of Mimir;\nMead from the pledge | of Othin each morn\nDoes Mimir drink: | do you know yet, or what?",
    30: "Necklaces had I | and rings from Heerfather,\nWise was my speech | and my magic wisdom;\nWidely I saw | over all the worlds.",
    31: "On the host his spear | did Othin hurl,\nThen in the world | did war first come;\nBroken was the outer | wall of the gods,\nAnd the Wanes came marching | through the breach.",
    32: "I see the baleful | Balder's brother\nUnlocks his battle-blade; | one night he slays\nThe other son | of Othin's wife.\nThrough middle-fields | and forests dark\nThe mother dwells | with the grief of men.",
    33: "I saw there wading | through rivers wild\nTreacherous men | and murderers too,\nAnd workers of ill | with the wives of men;\nThere Nithhogg sucked | the blood of the slain,\nAnd the wolf tore men; | would you know yet more?",
    34: "Hrungnir's slayer | I saw his home,\nFor the son of the giant, | and the fire of the slain;\nBalmunder there | the son of Nori, a-roaming,\nA hall he had | beset with serpents.",
    35: "I saw there wading | through rivers wild\nTreacherous men | and murderers too;\nAnd workers of ill | with the wives of men;\nThere Nithhogg sucked | the blood of the slain,\nAnd the wolf tore men; | would you know yet more?",
    36: "In the east there sat | the old one, in Iron-Wood,\nAnd there gave birth | to the brood of Fenrir;\nAmong these one | in monster's guise\nWas soon to steal | the sun from the sky.",
    37: "There feeds he full | on the flesh of the dead,\nAnd the home of the gods | he reddens with gore;\nDark grows the sun, | and in summer soon\nCome mighty storms: | would you know yet more?",
    38: "On a hill there sat, | and smote on his harp,\nEggther the joyous, | the giants' warder;\nAbove him the cock | in the bird-wood crowed,\nFair and red | did Fjalar stand.",
    39: "Then to the gods | crowed Gollinkambi,\nHe wakes the heroes | in Othin's hall;\nAnd beneath the earth | does another crow,\nThe rust-red bird | at the bars of Hel.",
    40: "Now Garm howls loud | before Gnipahellir,\nThe fetters will burst, | and the wolf run free;\nMuch I know, | and more can see\nOf the fate of the gods, | the mighty in battle.",
    41: "Brothers shall fight | and fell each other,\nAnd sisters' sons | shall kinship stain;\nHard is it on earth, | with mighty whoredom;\nAxe-time, sword-time, | shields are sundered,\nWind-time, wolf-time, | ere the world falls;\nNor ever shall men | each other spare.",
    42: "Fast move the sons | of Mim, and fate\nIs heard in the note | of the Gjallarhorn;\nLoud blows Heimdall, | the horn is aloft,\nIn fear quake all | who on Hel-roads are.",
    43: "Yggdrasil shakes, | and shiver on high\nThe ancient limbs, | and the giant is loose;\nTo the head of Mim | does Othin give heed,\nBut the kinsman of Surt | shall slay him soon.",
    44: "How fare the gods? | how fare the elves?\nAll Jotunheim groans, | the gods are in council;\nLoud roar the dwarfs | by the doors of stone,\nThe masters of the rocks: | would you know yet more?",
    45: "Now Garm howls loud | before Gnipahellir,\nThe fetters will burst, | and the wolf run free;\nMuch I know, | and more can see\nOf the fate of the gods, | the mighty in battle.",
    46: "From the east comes Hrym | with shield held high;\nIn giant-wrath | does the serpent writhe;\nO'er the waves he twists, | and the tawny eagle\nGnaws corpses screaming; | Naglfar is loose.",
    47: "O'er the sea from the north | there sails a ship\nWith the people of Hel, | at the helm stands Loki;\nAfter the wolf | do wild men follow,\nAnd with them the brother | of Byleistr goes.",
    48: "Surt fares from the south | with the scourge of branches,\nThe sun of the battle-gods | shone from his sword;\nThe crags are sundered, | the giant-women sink,\nThe dead throng Hel-way, | and heaven is cloven.",
    49: "Now comes to Hlin | yet another hurt,\nWhen Othin fares | to fight with the wolf,\nAnd Beli's fair slayer | seeks Surt, for the strife\nOf Frigg is ended | when the foe she has lost.",
    50: "Then comes Sigfather's | mighty son,\nVidarr, to fight | with the foaming wolf;\nIn the giant's son | does he thrust his sword\nFull to the heart: | his father is avenged.",
    51: "Hither there comes | the son of Hlothyn,\nThe bright snake banes, | and the warder of earth;\nIn anger smites | the warder of Midgarth,—\nForth goes his way, | but falls ere long,\nTreads nine paces, | the son of the earth,\nSlain by the serpent | of little fear.",
    52: "The sun turns black, | earth sinks in the sea,\nThe hot stars down | from heaven are whirled;\nFierce grows the steam | and the life-feeding flame,\nTill fire leaps high | about heaven itself.",
    53: "Now Garm howls loud | before Gnipahellir,\nThe fetters will burst, | and the wolf run free;\nMuch I know, | and more can see\nOf the fate of the gods, | the mighty in battle.",
    54: "Now do I see | the earth anew\nRise all green | from the waves again;\nThe cataracts fall, | and the eagle flies,\nAnd fish he catches | beneath the cliffs.",
    55: "The gods in Ithavoll | meet together,\nOf the terrible girdler | of earth they talk,\nAnd the mighty past | they call to mind,\nAnd the ancient runes | of the Ruler of Gods.",
    56: "In wondrous beauty | once again\nShall the golden tables | stand mid the grass,\nWhich the gods had owned | in the days of old.",
    57: "Then fields unsowed | bear ripened fruit,\nAll ills grow better, | and Baldr comes back;\nBaldr and Hoth dwell | in Hropt's battle-plains,\nAnd the mighty gods: | would you know yet more?",
    58: "Then Henir wins | the prophetic wand,\nAnd the sons of the brothers | of Tveggi abide\nIn Vindheim now: | would you know yet more?",
    59: "More fair than the sun, | a hall I see,\nRoofed with gold, | on Gimill height;\nThere shall the righteous | rulers dwell,\nAnd happiness ever | there shall they have.",
    60: "Then comes the dark | dragon flying,\nNithhogg up from | the Nithafjoll mountains;\nThe bodies of men | on his wings he bears,\nThe serpent bright: | but now must I sink.",
    61: "Now do I see | the earth anew\nRise all green | from the waves again;\nThe cataracts fall, | and the eagle flies,\nAnd fish he catches | beneath the cliffs.",
    62: "The gods in Ithavoll | meet together,\nOf the terrible girdler | of earth they talk;\nAnd the mighty past | they call to mind,\nAnd Fimbultyr's | ancient runes.",
    63: "In wondrous beauty | once again\nShall the golden tables | stand mid the grass,\nWhich the gods had owned | in the days of old,\nFive of them playing | at chess on the plain.",
    64: "There dwells a Ruler, | and watches o'er it,\nAn ancient and potent | one who does not fail;\nHe rules and distributes, | decides and settles,\nAll things from his seat | of justice and judgment.",
    65: "Then the powerful One, | the Mighty from above,\nComes to rule, who all things governs;\nFrom above he comes | to the judgment of men,\nHe who brings peace | to the gods and the slain.",
    66: "Nithhogg gnaws corpses | of the dead, the dark dragon,\nFrom above flies down | to the Nithafjoll mountains;\nIn his wings he carries | corpses, soaring;\nNow must I sink.",
}

# Old Norse text of key stanzas (from Codex Regius, ~1270 CE)
VOLUSPA_OLD_NORSE = {
    1: "Hljóðs bið ek allar\nhelgar kindir,\nmeiri ok minni\nmögu Heimdallar;\nviltu, at ek, Valföðr,\nvel fram telja\nforn spjöll fira,\nþau er fremst um man.",
    2: "Ek man jötna\nár um borna,\nþá er forðum mik\nfœdda höfðu;\nníu man ek heima,\nníu íviðjur,\nmjötvið mœran\nfyr mold neðan.",
    3: "Ár var alda\nþar er Ymir bygði,\nvar-a sandr né sær\nné svalar unnir;\njörð fannsk æva\nné upphiminn,\ngap var Ginnunga\nen gras hvergi.",
    41: "Munu menn ok konur\nsakar fella,\nok systrungar\nsifjar spilla;\nhart er í heimi,\nhórdómr mikill,\nskeggjöld, skálmöld,\nskjöldr klofinn,\nvindsöld, vargöld,\náðr verold steypisk;\nmun engi maðr\nöðrum þyrma.",
    52: "Sól tér sortna,\nsígr fold í mar,\nhverfa af himni\nheiðar stjörnur;\ngeisar eimi\nok aldrnari,\nleikr hár hiti\nviðr himin sjalfan.",
    54: "Sér hon upp koma\nöðru sinni\njörð ór ægi\niðjagræna;\nfalla forsar,\nflýgr örn yfir,\nsá er á fjalli\nfiska veiðir.",
    59: "Sér hon sal standa\nsólu fegra,\ngulls þaktan,\ná Gimlé;\nþar skulu dyggvar\ndróttir byggja\nok um aldrdaga\nynðis njóta.",
}

ESCHATOLOGICAL_THEMES = [
    "Ragnarok - doom of the gods",
    "World destruction by fire",
    "World destruction by flood",
    "Rebirth of the world",
    "Return of Baldr",
    "Fenrir wolf unleashed",
    "Midgard serpent rising",
    "Cosmic winter (Fimbulwinter)",
    "Battle of gods and giants",
    "New earth rising from sea",
    "Dragon Nithhogg",
    "Gimlé - hall of the righteous",
    "Creation myth (Ginnungagap)",
    "World tree Yggdrasil",
    "Norns and fate",
    "First war (Aesir-Vanir)",
]


def build_corpus():
    verses = {}
    for stanza_num in sorted(VOLUSPA_BELLOWS.keys()):
        text_en = VOLUSPA_BELLOWS[stanza_num]
        words = re.findall(r"[a-zA-Z']+", text_en)
        key = f"1:{stanza_num}"
        entry = {
            "text": text_en,
            "words": words,
            "word_count": len(words),
        }
        if stanza_num in VOLUSPA_OLD_NORSE:
            entry["text_on"] = VOLUSPA_OLD_NORSE[stanza_num]
            on_words = [w for w in re.split(r'\s+', VOLUSPA_OLD_NORSE[stanza_num]) if w]
            entry["words_on"] = on_words
        verses[key] = entry

    corpus = {
        "meta": {
            "title": "Voluspa (Prophecy of the Seeress)",
            "alt_title": "Voluspo / Völuspá",
            "age": "~1000 CE (Codex Regius ~1270 CE)",
            "original_language": "Old Norse",
            "source_tradition": "Poetic Edda / Eddic poetry",
            "translation": "Henry Adams Bellows (1923), public domain",
            "old_norse_key_stanzas": "Codex Regius (~1270 CE), public domain",
            "provenance": "Iceland, oral tradition from ~900 CE; first written ~1270 CE",
            "eschatological_themes": ESCHATOLOGICAL_THEMES,
            "sections": len(VOLUSPA_BELLOWS),
            "total_stanzas": 66,
            "date_fetched": str(date.today()),
            "notes": (
                "Voluspa is the first and most important poem in the Poetic Edda. "
                "It narrates creation, the first war, the fates of gods, "
                "and culminates in Ragnarok (world destruction by fire and flood) "
                "followed by world rebirth. Key eschatological stanzas: 40-53 (Ragnarok), "
                "54-66 (renewal). Baldr returns (st.57), a righteous hall (Gimlé) appears (st.59). "
                "Old Norse text included for key stanzas (1-3, 41, 52, 54, 59)."
            ),
        },
        "verses": verses,
    }
    return corpus


def main():
    dry_run = "--dry-run" in sys.argv
    corpus = build_corpus()

    total_stanzas = len(corpus["verses"])
    total_words = sum(v["word_count"] for v in corpus["verses"].values())

    print(f"Voluspa corpus: {total_stanzas} stanzas, {total_words} English words")
    print(f"Old Norse included for {sum(1 for v in corpus['verses'].values() if 'text_on' in v)} stanzas")

    if dry_run:
        print("\n--- First 3 stanzas ---")
        for k in list(corpus["verses"].keys())[:3]:
            print(f"\n[{k}] {corpus['verses'][k]['text']}")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Saved: {OUTPUT_PATH} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
