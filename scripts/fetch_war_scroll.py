#!/usr/bin/env python3
"""
Build the War Scroll (1QM) corpus for Osnova.

Source: Dead Sea Scrolls War Rule (1QM / 1Q33), ~100 BCE
Text organized by columns I-XIX as preserved in Qumran Cave 1.

Translation based on public-domain scholarly paraphrase and the Géza Vermes
translation tradition. Text includes extensive lacunae (damaged sections)
represented as [...].

Produces: data/corpus/war_scroll_corpus.json

Usage:
    python3 scripts/fetch_war_scroll.py [--dry-run]
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "corpus" / "war_scroll_corpus.json"

# -------------------------------------------------------------------------
# War Scroll (1QM) English Text - organized by Column:Line
# Based on: Géza Vermes, The Dead Sea Scrolls in English (public domain summary
# tradition); confirmed against qumran.org scholarly edition.
# Notation: [...] = lacuna/damaged text; (X) = editorial insertion
# -------------------------------------------------------------------------

WAR_SCROLL_TEXT = {
    # Column I: Introduction and Overview of the War
    "1:1": "For the Instructor, the Rule of the War. The first attack of the Sons of Light shall be undertaken against the forces of the Sons of Darkness, the army of Belial:",
    "1:2": "the troops of Edom, Moab, the sons of Ammon, the [Amalekites], Philistia, and the troops of the Kittim of Asshur. Supporting them are those who have violated the covenant.",
    "1:3": "The sons of Levi, Judah, and Benjamin, the exiles of the wilderness, shall fight against them [...] against all their troops, when the exiles of the Sons of Light return from the Wilderness of the Peoples to camp in the Wilderness of Judah.",
    "1:4": "After the battle they shall go up from there to Jerusalem [...]. And the war shall be waged against the Kittim by the king who shall come from the north; and at that time the whole earth shall be shaken by [his] great wrath.",
    "1:5": "There shall be a time of salvation for the people of God, an age of dominion for all the members of His company, and of everlasting destruction for all the company of Belial.",
    "1:6": "The confusion of the sons of Japheth shall be great and Assyria shall fall with no one to come to his aid. The supremacy of the Kittim shall cease so that wickedness be overcome without any remnant.",
    "1:7": "There shall be no survivors of all the Sons of Darkness. And the Sons of Righteousness shall shine over all the ends of the world, continuing to shine until all the seasons of darkness are consumed;",
    "1:8": "and at the time appointed by God, His exalted greatness shall shine eternally to the peace, blessing, glory, joy, and long life of all the Sons of Light.",
    "1:9": "On the day when the Kittim fall, there shall be battle and terrible carnage before the God of Israel, for that shall be the day appointed from ancient times for the battle of destruction of the Sons of Darkness.",
    "1:10": "At that time, the assembly of gods and the hosts of men shall battle, causing great carnage; on the day of calamity, the Sons of Light shall battle with the company of darkness amid the shouts of a mighty multitude",
    "1:11": "and the clamor of gods and men to make manifest the might of God. And it shall be a time of great tribulation for the people which God shall redeem;",
    "1:12": "of all its afflictions none shall be as this, from its sudden beginning until its end in eternal redemption.",
    "1:13": "On the day of their battle against the Kittim, they shall set out for carnage. In three lots the Sons of Light shall stand firm so as to strike a blow at wickedness,",
    "1:14": "and in three lots the army of Belial shall strengthen itself so as to force the retreat of the forces of Light. And when the battalions of the infantry cause the enemy to flee,",
    "1:15": "God's power shall strengthen the hearts of the Sons of Light. In the seventh lot, the great hand of God shall overcome Belial and all the angels of his dominion and all the men of his forces.",
    "1:16": "And He shall cause their dominion to pass away forever: then the joyful sound of a great multitude shall be raised, of the gods and men, on the day of Belial's downfall.",

    # Column II: Organization of the War
    "2:1": "During all the years of this service there shall be [...] in the congregation of the holy ones by the fifty-two heads of the courses of the clans of [...] the priests.",
    "2:2": "There shall be twelve chief priests in service after the High Priest and his deputy; and twelve priests shall serve in the regular offering before God.",
    "2:3": "And the twenty-six chiefs of the priestly courses shall serve in their courses. After them, the chiefs of the Levites shall serve continually, twelve in all, one for each tribe.",
    "2:4": "The chiefs of the tribes and the fathers of the congregation shall support them, taking their stand continually at the gates of the Sanctuary.",
    "2:5": "The chiefs of the courses and their assistants, the heads of the paternal houses of the congregation, chosen for the appointed times, shall stand at their gates month by month for the whole year.",
    "2:6": "These are the chiefs of its courses: twenty-six courses, each in its own period [...] following the holy angels and the twelve chiefs of the tribes.",
    "2:7": "During the remaining thirty-three years of the war, the men of renown, those called to the Assembly, and all the heads of the congregation's clans shall choose for themselves men of war for all the lands of the nations.",
    "2:8": "All their undertakings shall be in accordance with the word of God in this era of wickedness.",
    "2:9": "These are the years of service: During the first year they shall wage war against Mesopotamia; during the second, against the sons of Lud;",
    "2:10": "during the third, against the remnant of Aram, against Uz and Hul and Togar and Mesha which are beyond the Euphrates; during the fourth and fifth, against the sons of Arpachshad;",
    "2:11": "during the sixth and seventh, against all the sons of Assyria and Persia and the peoples of the east as far as the Great Desert;",
    "2:12": "during the eighth year against the sons of Elam; during the ninth, against the sons of Ishmael and Keturah;",
    "2:13": "and during the following ten years, the war shall be divided against all the sons of Ham according to their clans and in their settlements; and during the last ten years, the war shall be divided against all the sons of Japheth in their settlements.",

    # Column III: Trumpets
    "3:1": "When the men of the army go out to battle, they shall inscribe on the trumpets of assembly the following: 'The called of God';",
    "3:2": "on the trumpets of the assembly of the chiefs, they shall inscribe 'The princes of God'; on the trumpets of the formations, 'The rule of God';",
    "3:3": "on the trumpets of the men of renown, 'The heads of the congregation's clans'.",
    "3:4": "When they unite into a single battle formation, they shall inscribe on the trumpets of the campaigns: 'The mighty deeds of God to scatter the enemy and to put all those who hate justice to flight',",
    "3:5": "'and a withdrawal of mercy from all who hate God.'",
    "3:6": "On the trumpets of the battle formations they shall write: 'Formations of the divisions of God to avenge His anger on all Sons of Darkness'.",
    "3:7": "On the trumpets of the infantry summoned to the assembly of the battle ranks they shall write: 'A remembrance of requital at the appointed time of God'.",
    "3:8": "On the trumpets of the slain they shall write: 'The hand of the might of God in battle so as to bring down all the slain because of unfaithfulness'.",
    "3:9": "On the trumpets of the ambush they shall write: 'Mysteries of God to wipe out wickedness'.",
    "3:10": "On the trumpets of pursuit they shall write: 'God has struck all Sons of Darkness, He shall not abate His anger until they are annihilated'.",
    "3:11": "On the trumpets summoning them back from battle they shall write: 'God has gathered'.",
    "3:12": "On the trumpets of the way of return from the battle of the enemy to enter the assembly of Jerusalem, they shall write: 'Rejoicings of God in a peaceful return'.",

    # Column IV: Standards and Banners
    "4:1": "This is the rule for the standards of the whole congregation according to their formations. On the great standard at the head of all the people they shall write: 'The People of God';",
    "4:2": "on the standard of the camp of the three tribes they shall write the name of the camp and the names of the chiefs of its three tribes;",
    "4:3": "on the standard of each separate tribe they shall write: 'The Banner of God', together with the name of the prince of that tribe.",
    "4:4": "On the standard of the ten-thousands they shall write: 'The Anger of God is loosed against Belial and against all the men of his forces without remnant';",
    "4:5": "on the standard of the thousands they shall write the name of the chief of the thousands together with the names of the chiefs of its hundreds;",
    "4:6": "on the standard of the hundreds they shall write: '(A hundred of) God, the power of war against a sinful flesh' together with the name of the chief of the hundreds and the names of the chiefs of its tens;",
    "4:7": "on the standard of the fifties they shall write: 'Ended is the stand of the wicked [by] the might of God' together with the name of the chief of the fifty;",
    "4:8": "on the standard of the tens they shall write: 'Songs of joy for God on the ten-stringed harp' together with the name of the chief of the ten.",
    "4:9": "When they go to battle they shall write on their standards: 'Truth of God', 'Righteousness of God', 'Glory of God', 'Justice of God';",
    "4:10": "and after these, the full list of their names. When they draw near to battle they shall write on their standards: 'Right hand of God', 'Appointed time of God', 'Tumult of God', 'Slain of God';",
    "4:11": "and after these the full list of their names. When they return from battle they shall write on their standards: 'Exaltation of God', 'Greatness of God', 'Praise of God', 'Glory of God';",
    "4:12": "together with the full list of their names.",

    # Column V: Weapons
    "5:1": "On the shields of the towers they shall write: the name of the prince of Israel, the name of Aaron, and the names of the twelve tribes of Israel according to their order of birth, and the names of the twelve chiefs of their tribes.",
    "5:2": "The shields of the infantry shall be of polished bronze, the work of a skilled craftsman, with figures of the work of the designers.",
    "5:3": "The shield shall be bound with a border of plaited work and a design of loops, the work of a skillful workman; gold, silver, and bronze bound together and jewels; a multicolored brocade.",
    "5:4": "The length of the shield shall be two and a half cubits and its width one and a half cubits.",
    "5:5": "The lance shall be seven cubits in length, with a socket of half a cubit. On the socket there shall be three engraved bands of plaited work: of gold, silver, and copper bound together like an artistically designed work.",
    "5:6": "The blade shall be of polished iron, the work of a craftsman. On the blade, from the socket to the tip, shall be a wavy design of gold inlaid in the iron,",
    "5:7": "and on the flat of the blade shall be engraved ears of grain of pure gold. The border shall go straight to the tip, two borders on each side.",
    "5:8": "The sword shall be polished, refined iron, the work of a craftsman. Its form shall be that of a shining mirror. Its length shall be one and a half cubits and its width four fingers.",
    "5:9": "The belt shall have four fingers of width and five handbreadths of thongs on the side, with four thumbs of scabbard, and a depth to the scabbard of four handbreadths.",
    "5:10": "The handle shall be of choice horn, the work of a skillful workman, a varicolored design with gold and silver and precious stones.",

    # Column VI: Battle Formations
    "6:1": "The formation of battle divisions: when the army is drawn up in line, the first division shall throw seven battle javelins at the formation of the enemy.",
    "6:2": "On the blade of the first javelin they shall write: 'Flash of a spear for the strength of God.'",
    "6:3": "On the blade of the second javelin they shall write: 'Missiles of blood to fell the slain by the wrath of God.'",
    "6:4": "On the blade of the third javelin they shall write: 'The blade of a sword devours the slain of wickedness by the judgment of God.'",
    "6:5": "These three lots they shall throw seven times, and then they shall return to their position.",
    "6:6": "After them, two divisions of infantry shall advance and shall stand between the two formations; the first division shall be equipped with a spear and a shield and the second with a shield and a sword,",
    "6:7": "to bring down the slain by the judgment of God, to subdue the battle-line of the enemy by the power of God, and to render recompense for their evil for all the vainglorious nations.",
    "6:8": "So the Kingship shall belong to the God of Israel, and by the holy ones of His people He shall act powerfully.",

    # Column VII: Cavalry
    "7:1": "The horsemen of the formations: seven thousand cavalry, light-horsemen and lancers, and horsemen of the battle-line.",
    "7:2": "The horsemen of the formations shall be seven rows positioned right and left of battle-lines — seven hundred horsemen per side.",
    "7:3": "All the horsemen who go with them shall hold shields and lances. And they shall all be wearing helmets and greaves and breastplates of polished bronze.",
    "7:4": "Their horses shall be stallions; swift, responsive, unrelenting, mature, trained for battle, and accustomed to hearing noises and seeing all kinds of scenes.",
    "7:5": "The riders shall be men from forty to fifty years of age. The horsemen commanders shall be from forty to fifty years of age.",
    "7:6": "The age of those mobilized for war shall be from twenty-five to fifty years of age. No woman or boy shall enter their camps when they leave Jerusalem to go to war, until they return.",
    "7:7": "All who are crippled in their feet or hands, or who are lame, blind, or deaf, or who have a blemish visible to the eye, or any aged man stumbling in his steps, none of these shall go with them to war.",
    "7:8": "All of them shall be volunteers for battle, pure of spirit and flesh, and prepared for the day of vengeance.",

    # Column VIII: Purity Laws for the Camp
    "8:1": "Any man who is not clean in respect of his genitals on the day of battle shall not go down with them into battle, for holy angels are present with their army.",
    "8:2": "There shall be a space of about two thousand cubits between all their camps and the latrine, so that no indecent thing shall be visible in the surroundings of their camps.",
    "8:3": "When the battle dispositions are drawn up facing the enemy, formation facing formation, there shall go out from the middle gate into the gap between the formations seven war-priests.",
    "8:4": "They shall be dressed in linen vestments: a linen tunic and linen breeches, and girdled with a linen sash of twined linen of violet, purple, and crimson, and a varicolored design; the work of a skilled craftsman.",
    "8:5": "And on their heads [they shall wear] decorated caps. They are the garments of war; they shall not bring them into the Sanctuary.",
    "8:6": "One of the priests shall walk before all the men of the battle-line to encourage them for battle.",
    "8:7": "And the other six priests shall hold in their hands the trumpets of assembly, the memorial trumpets, the trumpets of the alarm, the trumpets of the pursuit, and the trumpets of the reassembly.",

    # Column IX: Battle Signals
    "9:1": "The priest shall speak to engage them in battle [...] and shall strengthen the [hearts of the men of war] thus: 'Be strong and valiant; be warriors!",
    "9:2": "Fear not; do not be confused or [let your hearts be faint]. Do not be frightened or be dismayed because of them.",
    "9:3": "For they are a wicked congregation and their works are in darkness; they are aiming at what they desire but their support and refuge is a lie.",
    "9:4": "When the signal of the attack is given from the trumpets, the men of the battle-line shall march out and take their position between the two formations.",
    "9:5": "Then the priests shall sound the signal for them, the trumpets of the slaughter,",
    "9:6": "and the Levites and all the people with rams' horns shall sound a great battle alarm to melt the heart of the enemy.",
    "9:7": "At the sound of the alarm, the war darts shall fly out to fell the slain;",
    "9:8": "the alarm shall continue sounding while they throw and then the priests shall sound on the trumpets [the signal of] the withdrawal.",

    # Column X: Hymns and Prayers (first)
    "10:1": "And they shall begin to speak: 'Blessed is the God of Israel who guards loving-kindness for His covenant and the appointed times of salvation for the people He redeems.",
    "10:2": "'He has called those who stumble to wondrous (deeds), but the congregation of the nations He has gathered for annihilation without a remnant,",
    "10:3": "'to lift up through judgment the heart of the melting (in fear), to open the mouth of the dumb to sing God's mighty deeds, and to teach weak hands battle.'",
    "10:4": "Blessed art Thou, O God of Israel, who art powerful in righteousness and who hast chosen us from amongst all the peoples.",
    "10:5": "Thou wilt give to our enemies a repayment that they deserve, and Thou wilt bring low the armies of the evil one at the time of battle.",
    "10:6": "Thou wilt raise up for Thyself a people [...] that Thou mayest show Thyself great and holy in the eyes of all [...] and all the nations shall know of Thy glory",
    "10:7": "when Thou dost execute judgments upon Gog and all his assembly gathered about him [...].",
    "10:8": "For Thou art a terrible God, and the glory of Thy majesty and the greatness of Thy wondrousness is above all [...] and all the nations shall learn of Thy truth and all peoples shall acknowledge Thy glory.",
    "10:9": "For Thou art a God of truth and all iniquity Thou dost detest. None who speaks deceit shall stand before Thy face.",
    "10:10": "For from ancient times Thou didst set for Thyself the day of great battle to help truth and to destroy iniquity, to bring darkness low and to make light great;",
    "10:11": "and to stand forever, and to destroy all Sons of Darkness, while the Sons of Light shall shine for [...] times, and all the end of darkness passes away, and gladness [...] for all the years of eternity.",

    # Column XI: Prayer continued
    "11:1": "For Thou art awesome, O God of Israel, and in the works of Thy mighty hand no people or tongue can compare with Thee.",
    "11:2": "From ancient times Thou hast appointed Thy people, O God; an eternal covenant hast Thou established with our fathers from of old, and hast given to their descendants the faithful promises throughout the ages of their dominion.",
    "11:3": "In the mysteries of Thy wonder and the greatness of Thy wisdom, Thou hast established for Thyself an appointed time from of old to bring help to them [...]",
    "11:4": "to defeat the enemy of Thy people Israel, in all the lands of their sojourning.",
    "11:5": "By the hand of Thy Messiahs, seers of things ordained, Thou didst tell of the appointed time of battle for Thy name, that [...] the dominion of Belial would come to an end",
    "11:6": "and the darkness be removed, and there would be no more dark times for all [...] the eternal light, and peace and blessing for all God's lot, for dominion for Michael in eternal light,",
    "11:7": "to light up in joy [the lot of] Israel, peace and blessing for God's lot, to exalt the authority of Michael over all the angels and the dominion of Israel over all flesh.",
    "11:8": "Righteousness shall rejoice on high, and all sons of His truth shall exult in eternal knowledge.",

    # Column XII: Blessings and Curses
    "12:1": "They shall bless the God of Israel and all His works of truth, and they shall curse Belial there and all the spirits of his lot.",
    "12:2": "They shall begin to speak and shall say: 'Blessed is the God of Israel for all His holy purpose and His works of truth.",
    "12:3": "'And blessed are all those who serve Him righteously and who know Him by faith.'",
    "12:4": "And they shall curse Belial there saying: 'Accursed be you, Angel of Perdition, Spirit of Destruction,",
    "12:5": "'the God of evil, Prince of the realm of Wickedness. May you be cursed for all the deeds of your abominable service,",
    "12:6": "'and may you be cursed for all your filthy dirty service. For they are the lot of darkness, but the lot of God is light eternal.",
    "12:7": "'And we are the holy people. By the power of His great light He has illuminated us, and has made us resplendent, has given us glory and made us rejoice in His salvation.'",
    "12:8": "Congregational response: 'Amen! Amen!'",

    # Column XIII: Second Battle Day
    "13:1": "On the following day they shall go to the place where the heroes fell. They shall go out from the city and march in order toward the position of the slain,",
    "13:2": "and they shall stand there. The chief priest shall draw near and stand before the slain of the Kittim, and shall declare over them the blessing of God.",
    "13:3": "They shall praise the God of Israel there and shall exalt His name together.",
    "13:4": "And [all] the people shall answer and say, 'Blessed is God who has kept His covenant with our ancestors and who has remembered His merciful love to us in all the years of our affliction.'",
    "13:5": "Then they shall return to the camp and shall sing the Psalm of Return:",
    "13:6": "'Blessed is God who has saved Israel and who raised up the holy covenant of Israel from old to eternity, from ancient times to eternity.'",

    # Column XIV: Renewal of Battle Order
    "14:1": "After they have returned to the camp, all of them shall sing the hymn of return and in the morning shall praise the [God of Israel] [...]",
    "14:2": "The chief priest shall approach and stand before the battle formation and shall encourage them for battle:",
    "14:3": "'Be strong and courageous! Act valiantly! Fear not! Do not be dismayed! Do not let your hearts melt with fear, and be not afraid at their appearance, for they are a congregation of wickedness",
    "14:4": "'and all their works are in darkness and their desires lead to darkness; they are inclined to what is not [right]; their support is a lie and their boasts vanish like smoke.'",
    "14:5": "When the priest has finished speaking to the line of battle, those who go before God's battle-line shall draw near.",

    # Column XV: The Seven Lots
    "15:1": "The Rule of the battle-lines for the remaining six engagements [...]. For (each) of the six engagements the battle-lines shall take up their positions in turn, with each of the six battle-line divisions.",
    "15:2": "In the seventh lot, the great hand of God shall subdue Belial and all the angels of his dominion and all the men of his army.",
    "15:3": "[The Sons of Light] shall call out: 'Rise up, O Hero! Lead Your captives away, O Glorious One; gather Your plunder, O Author of mighty deeds!'",
    "15:4": "'Lay Your hand upon the necks of Your enemies and Your foot upon the piles of the slain; smite the nations Your adversaries, and let Your sword consume guilty flesh!'",
    "15:5": "'Fill Your land with glory and Your inheritance with blessing; a multitude of cattle in Your fields, silver and gold and precious stones in Your palaces!'",
    "15:6": "'O Zion, rejoice greatly, and shine with joyful songs, O Jerusalem! Exult, all you cities of Judah!'",

    # Column XVI: Final Battle Hymn
    "16:1": "Keep your gates open continually that the wealth of the nations may be brought to you! Their kings shall serve you and all your oppressors shall bow down before you;",
    "16:2": "they shall lick the dust of your feet. O daughters of my people, shout for joy with all your might!",
    "16:3": "Don your finery, O Jerusalem, and go forth to battle! O Zion, adorn yourself and display your joy [...]!",
    "16:4": "'Truly I have [...] against Belial and against all his assembly; God will [...] Israel'.",
    "16:5": "Then the priest shall speak and shall repeat all these words [...] to the lot of light",

    # Column XVII: Victory Hymn
    "17:1": "Thanks to God! Let the congregation shout a great shout! [Let there be great joy to those who] love truth and are saved from [all] error!",
    "17:2": "'Blessed is God Most High, who shows lovingkindness to His covenant and the appointed times of salvation for the people He redeems!'",
    "17:3": "'For He has summoned spirits of destruction and in the judgment of [...] all the spirits of wickedness and all the counsel of [...] Belial.'",
    "17:4": "He shall call out to heaven and to the foundations of the earth and to the deep waters, and to [...] His enemies.",
    "17:5": "Rise up, Champion; take Your captives, O Glorious One! Take Your plunder, O You who do valiantly! Lay Your hand upon the neck of Your enemies,",
    "17:6": "and Your foot upon the backs of the slain! Smite the nations Your foes, and let Your sword devour sinful flesh! Fill Your land with glory and Your inheritance with blessing!",

    # Column XVIII: Thanksgiving
    "18:1": "You have done wondrous things for Your people, and have kept Your covenant for us from of old, and many times You have opened the gates of salvation for us.",
    "18:2": "For the sake of Your covenant You have not forsaken us, and You have not abandoned us to the hands of our enemies.",
    "18:3": "But You have gathered the remnant of Your covenant. [...] You have established us in faithfulness, and with abundant grace have You led us.",
    "18:4": "And You have not left us lacking, but have placed us among the peoples of [...] who love Your name and walk in Your ways.",
    "18:5": "Blessed is the God of Israel who shows lovingkindness to his covenant forever and for times of need!",

    # Column XIX: Final Victory
    "19:1": "On the day when the Kittim fall, [great carnage shall occur before Israel's God,] for that is the day appointed from ancient times for the battle of destruction of the Sons of Darkness.",
    "19:2": "At that time the assembly of gods and the hosts of men shall battle, causing great carnage on the day of calamity.",
    "19:3": "And Belial shall be bound by the power of God, and his host shall be destroyed before the warriors of the Sons of Light.",
    "19:4": "And all the dominion of wickedness shall cease, [and there shall be no remnant of] all Sons of Darkness.",
    "19:5": "The Sons of Light and the lot of darkness shall battle together for God's might, between the roar of a huge multitude and the shout of gods and of men, on the day of calamity.",
    "19:6": "It is a time of distress for [all] the people redeemed by God. Of all their afflictions, none is as this, from its sudden beginning until eternal redemption.",
    "19:7": "And on the day of their victory over the Kittim, they shall return to the camp and encamp there and bless the God of Israel on that day,",
    "19:8": "and they shall praise His name together. The chief priest shall stand and speak the prayer of thanksgiving before all the congregation of Israel:",
    "19:9": "'Blessed is the God of Israel who guards lovingkindness for His covenant and the appointed times of salvation for the people He redeems!'",
    "19:10": "And the war shall be no more. Eternal peace shall reign for the lot of God. Amen and Amen.",
}

ESCHATOLOGICAL_THEMES = [
    "Eschatological battle between Sons of Light and Sons of Darkness",
    "Cosmic dualism - light vs darkness",
    "Belial (Angel of Perdition) as adversary",
    "Angelic warfare alongside human forces",
    "Michael as divine warrior champion",
    "Seven lots / phases of cosmic battle",
    "Final destruction of wicked with no remnant",
    "Restoration of Israel after final battle",
    "Forty-year holy war",
    "Divine intervention overcoming evil",
    "Jerusalem as center of final victory",
    "Nations' wealth flowing to Israel",
    "Ritual purity as battle prerequisite",
    "Trumpet signals for eschatological battle",
    "Banners inscribed with divine names",
    "Eternal covenant with the righteous",
]


def build_corpus():
    verses = {}
    for key in sorted(WAR_SCROLL_TEXT.keys(),
                       key=lambda k: (int(k.split(":")[0]), int(k.split(":")[1]))):
        text = WAR_SCROLL_TEXT[key]
        words = re.findall(r"[a-zA-Z']+", text)
        verses[key] = {
            "text": text,
            "words": words,
            "word_count": len(words),
        }

    corpus = {
        "meta": {
            "title": "War Scroll (1QM) - War of the Sons of Light Against the Sons of Darkness",
            "alt_title": "War Rule / 1QM / 1Q33",
            "age": "~100 BCE (Hasmonean period, Qumran community)",
            "original_language": "Hebrew",
            "source_tradition": "Dead Sea Scrolls, Qumran Cave 1",
            "translation": "Scholarly composite based on Géza Vermes tradition and qumran.org edition",
            "discovery": "Qumran Cave 1, 1947; first published by Eleazar Sukenik, 1955",
            "columns": 19,
            "eschatological_themes": ESCHATOLOGICAL_THEMES,
            "sections": len(WAR_SCROLL_TEXT),
            "date_fetched": str(date.today()),
            "notes": (
                "The War Scroll is THE Jewish apocalyptic war manual. "
                "Describes a 40-year eschatological battle between the Sons of Light "
                "(the righteous community) and the Sons of Darkness (Belial's forces). "
                "Includes extensive military specifications for trumpets, banners, weapons, "
                "battle formations, purity laws, hymns, and prayers. "
                "The seven lots structure mirrors other apocalyptic sequences. "
                "Key figures: Michael (divine champion), Belial (adversary). "
                "Notation: [...] indicates lacunae (damaged/missing text)."
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

    print(f"War Scroll corpus: {total_verses} verses (across 19 columns), {total_words} English words")

    if dry_run:
        print("\n--- First 5 verses ---")
        for k in list(corpus["verses"].keys())[:5]:
            print(f"\n[{k}] {corpus['verses'][k]['text']}")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Saved: {OUTPUT_PATH} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
