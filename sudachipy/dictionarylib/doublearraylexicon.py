import struct

from . import wordidtable
from . import wordinfolist
from . import wordparameterlist
from .lexicon import Lexicon
from .. import dartsclone


class DoubleArrayLexicon(Lexicon):

    __SIGNED_SHORT_MIN = -32768
    __SIGNED_SHORT_MAX = 32767
    __USER_DICT_COST_PER_MORPH = -20

    def __init__(self, bytes_, offset):
        self.trie = dartsclone.doublearray.DoubleArray()
        bytes_.seek(offset)
        size = int.from_bytes(bytes_.read(4), 'little')
        offset += 4
        bytes_.seek(offset)
        array = struct.unpack_from("<{}I".format(size), bytes_, offset)
        self.trie.set_array(array, size)
        offset += self.trie.total_size()

        self.word_id_table = wordidtable.WordIdTable(bytes_, offset)
        offset += self.word_id_table.storage_size()

        self.word_params = wordparameterlist.WordParameterList(bytes_, offset)
        offset += self.word_params.storage_size()

        self.word_infos = wordinfolist.WordInfoList(bytes_, offset, self.word_params.get_size())

    def lookup(self, text: str, offset: int) -> Lexicon.Itr:
        result = self.trie.common_prefix_search(text, offset)
        for item in result:
            word_ids = self.word_id_table.get(item[0])
            length = item[1]
            for word_id in word_ids:
                yield (word_id, length)

    def get_left_id(self, word_id: int) -> int:
        return self.word_params.get_left_id(word_id)

    def get_right_id(self, word_id: int) -> int:
        return self.word_params.get_right_id(word_id)

    def get_cost(self, word_id: int) -> int:
        return self.word_params.get_cost(word_id)

    def get_word_info(self, word_id: int) -> 'WordInfo':  # noqa: F821
        return self.word_infos.get_word_info(word_id)

    def size(self) -> int:
        return self.word_params.size

    def get_word_id(self, headword, pos_id, reading_form):
        for wid in range(self.word_infos.size()):
            info = self.word_infos.get_word_info(wid)
            if info.surface == headword \
                    and info.pos_id == pos_id \
                    and info.reading_form == reading_form:
                return wid
        return -1

    def get_dictionary_id(self, word_id: int) -> int:
        return 0

    def calculate_cost(self, tokenizer) -> None:
        for wid in range(len(self.word_params.size)):
            if self.get_cost(wid) != self.__SIGNED_SHORT_MIN:
                continue
            surface = self.get_word_info(wid).surface
            ms = tokenizer.tokenize(surface, None)
            cost = ms.get_internal_cost() + self.__USER_DICT_COST_PER_MORPH * len(ms)
            cost = min(cost, self.__SIGNED_SHORT_MAX)
            cost = max(cost, self.__SIGNED_SHORT_MIN)
            self.word_params.set_cost(wid, cost)
