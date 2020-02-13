from collections import OrderedDict, defaultdict

import attr
from pathlib import Path
from pylexibank import Concept, Language
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank import progressbar

from lingpy import *
from clldutils.misc import slug

@attr.s
class CustomConcept(Concept):
    French_Gloss = attr.ib(default=None)
    Latin_Gloss = attr.ib(default=None)
    Number = attr.ib(default=None)

@attr.s
class CustomLanguage(Language):
    Number = attr.ib(default=None)
    Canton = attr.ib(default=None)


class Dataset(BaseDataset):
    id = "tppsr"
    dir = Path(__file__).parent
    concept_class = CustomConcept
    language_class = CustomLanguage

    def cmd_makecldf(self, args):
        args.writer.add_sources()

        data = self.raw_dir.read_csv('ipa.tsv', delimiter='\t')
        args.writer.add_sources()
        
        concepts = {}
        for concept in self.concepts:
            args.writer.add_concept(
                    ID='{0}_{1}'.format(
                        concept['ID'],
                        slug(concept['FRENCH'])),
                    Number=concept['NUMBER'],
                    Name=concept['FRENCH'],
                    French_Gloss=concept['FRENCH'],
                    Latin_Gloss=concept['LATIN'],
                    Concepticon_ID=concept['CONCEPTICON_ID'],
                    Concepticon_Gloss=concept['CONCEPTICON_GLOSS']
                    )
            concepts[concept['NUMBER']] = '{0}_{1}'.format(
                    concept["ID"],
                    slug(concept['FRENCH']))
        languages = args.writer.add_languages(
                id_factory='Number')

        for line in progressbar(self.raw_dir.read_csv('graphemes.tsv', delimiter='\t')):
            args.writer.add_form(
                    Value=line[3],
                    Form=line[3],
                    Parameter_ID=concepts[line[1]],
                    Language_ID=line[2],
                    Source=['Gauchat1925'])
                    



