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

        data = self.raw_dir.read_csv('graphemes.tsv', delimiter='\t')
        args.writer.add_sources()
        
        concepts = {}
        for concept in self.conceptlists[0].concepts.values():
            idx = '{0}_{1}'.format(
                        concept.id,
                        slug(concept.attributes['french']))
            args.writer.add_concept(
                    ID=idx,
                    Number=concept.number,
                    Name=concept.attributes['french'],
                    French_Gloss=concept.attributes['french'],
                    Latin_Gloss=concept.attributes['latin'],
                    Concepticon_ID=concept.concepticon_id,
                    Concepticon_Gloss=concept.concepticon_gloss
                    )
            concepts[concept.number] = idx
            
        languages = args.writer.add_languages(
                id_factory='Number')

        for line in progressbar(self.raw_dir.read_csv('graphemes.tsv', delimiter='\t')):
            args.writer.add_form(
                    Value=line[3],
                    Form=line[3],
                    Parameter_ID=concepts[line[1]],
                    Language_ID=line[2],
                    Source=['Gauchat1925'])
                    



