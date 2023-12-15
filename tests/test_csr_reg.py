# amaranth: UnusedElaboratable=no

import unittest
from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.sim import *

from amaranth_soc.csr.reg import *
from amaranth_soc.csr import field, Element


def _silence_unused(*objs):
    for obj in objs:
        Fragment.get(obj, platform=None)


def _compatible_fields(a, b):
    return a.port.shape == b.port.shape and a.port.access == b.port.access


class FieldPortSignatureTestCase(unittest.TestCase):
    def test_shape_1_ro(self):
        sig = FieldPort.Signature(1, "r")
        self.assertEqual(sig.shape, unsigned(1))
        self.assertEqual(sig.access, FieldPort.Access.R)
        self.assertEqual(sig.members, wiring.Signature({
            "r_data": In(unsigned(1)),
            "r_stb":  Out(1),
            "w_data": Out(unsigned(1)),
            "w_stb":  Out(1),
        }).members)
        self.assertEqual(repr(sig),
                         "csr.FieldPort.Signature(SignatureMembers({"
                             "'r_data': In(unsigned(1)), "
                             "'r_stb': Out(1), "
                             "'w_data': Out(unsigned(1)), "
                             "'w_stb': Out(1)}))")

    def test_shape_8_rw(self):
        sig = FieldPort.Signature(8, "rw")
        self.assertEqual(sig.shape, unsigned(8))
        self.assertEqual(sig.access, FieldPort.Access.RW)
        self.assertEqual(sig.members, wiring.Signature({
            "r_data": In(unsigned(8)),
            "r_stb":  Out(1),
            "w_data": Out(unsigned(8)),
            "w_stb":  Out(1),
        }).members)

    def test_shape_10_wo(self):
        sig = FieldPort.Signature(10, "w")
        self.assertEqual(sig.shape, unsigned(10))
        self.assertEqual(sig.access, FieldPort.Access.W)
        self.assertEqual(sig.members, wiring.Signature({
            "r_data": In(unsigned(10)),
            "r_stb":  Out(1),
            "w_data": Out(unsigned(10)),
            "w_stb":  Out(1),
        }).members)

    def test_shape_0_rw(self):
        sig = FieldPort.Signature(0, "w")
        self.assertEqual(sig.shape, unsigned(0))
        self.assertEqual(sig.access, FieldPort.Access.W)
        self.assertEqual(sig.members, wiring.Signature({
            "r_data": In(unsigned(0)),
            "r_stb":  Out(1),
            "w_data": Out(unsigned(0)),
            "w_stb":  Out(1),
        }).members)

    def test_create(self):
        sig  = FieldPort.Signature(unsigned(8), "rw")
        port = sig.create(path=("foo", "bar"))
        self.assertIsInstance(port, FieldPort)
        self.assertEqual(port.shape, unsigned(8))
        self.assertEqual(port.access, FieldPort.Access.RW)
        self.assertEqual(port.r_stb.name, "foo__bar__r_stb")
        self.assertIs(port.signature, sig)

    def test_eq(self):
        self.assertEqual(FieldPort.Signature(8, "r"), FieldPort.Signature(8, "r"))
        self.assertEqual(FieldPort.Signature(8, "r"), FieldPort.Signature(8, FieldPort.Access.R))
        # different shape
        self.assertNotEqual(FieldPort.Signature(8, "r"), FieldPort.Signature(1, "r"))
        # different access mode
        self.assertNotEqual(FieldPort.Signature(8, "r"), FieldPort.Signature(8, "w"))
        self.assertNotEqual(FieldPort.Signature(8, "r"), FieldPort.Signature(8, "rw"))
        self.assertNotEqual(FieldPort.Signature(8, "w"), FieldPort.Signature(8, "rw"))

    def test_wrong_shape(self):
        with self.assertRaisesRegex(TypeError,
                r"Field shape must be a shape-castable object, not 'foo'"):
            port = FieldPort.Signature("foo", "rw")

    def test_wrong_access(self):
        with self.assertRaisesRegex(ValueError, r"'wo' is not a valid FieldPort.Access"):
            port = FieldPort.Signature(8, "wo")


class FieldPortTestCase(unittest.TestCase):
    def test_simple(self):
        sig  = FieldPort.Signature(unsigned(8), "rw")
        port = FieldPort(sig, path=("foo", "bar"))
        self.assertEqual(port.shape, unsigned(8))
        self.assertEqual(port.access, FieldPort.Access.RW)
        self.assertEqual(port.r_stb.name, "foo__bar__r_stb")
        self.assertIs(port.signature, sig)
        self.assertEqual(repr(port),
                         "csr.FieldPort(csr.FieldPort.Signature(SignatureMembers({"
                             "'r_data': In(unsigned(8)), "
                             "'r_stb': Out(1), "
                             "'w_data': Out(unsigned(8)), "
                             "'w_stb': Out(1)})))")

    def test_wrong_signature(self):
        with self.assertRaisesRegex(TypeError,
                r"This interface requires a csr\.FieldPort\.Signature, not 'foo'"):
            FieldPort("foo")


class FieldTestCase(unittest.TestCase):
    def test_create(self):
        class MockField(wiring.Component):
            def __init__(self, shape, *, reset):
                super().__init__({"port": Out(FieldPort.Signature(shape, "rw"))})
                self.reset = reset

            def elaborate(self, platform):
                return Module()

        field_u8 = Field(MockField, unsigned(8), reset=1).create()
        self.assertEqual(field_u8.port.shape, unsigned(8))
        self.assertEqual(field_u8.reset, 1)
        _silence_unused(field_u8)

    def test_create_multiple(self):
        class MockField(wiring.Component):
            port: Out(FieldPort.Signature(unsigned(8), "rw"))

            def elaborate(self, platform):
                return Module()

        field_1 = Field(MockField).create()
        field_2 = Field(MockField).create()
        self.assertIsNot(field_1, field_2)
        _silence_unused(field_1, field_2)


class FieldMapTestCase(unittest.TestCase):
    def test_simple(self):
        field_map = FieldMap({
            "a": Field(field.R, unsigned(1)),
            "b": Field(field.RW, signed(3)),
            "c": {"d": Field(field.RW, unsigned(4))},
        })

        field_r_u1  = Field(field.R, unsigned(1)).create()
        field_rw_s3 = Field(field.RW, signed(3)).create()
        field_rw_u4 = Field(field.RW, unsigned(4)).create()

        self.assertTrue(_compatible_fields(field_map["a"], field_r_u1))
        self.assertTrue(_compatible_fields(field_map["b"], field_rw_s3))
        self.assertTrue(_compatible_fields(field_map["c"]["d"], field_rw_u4))

        self.assertTrue(_compatible_fields(field_map.a, field_r_u1))
        self.assertTrue(_compatible_fields(field_map.b, field_rw_s3))
        self.assertTrue(_compatible_fields(field_map.c.d, field_rw_u4))

        self.assertEqual(len(field_map), 3)

        _silence_unused(*(v for k, v in field_map.flatten()))
        _silence_unused(field_r_u1, field_rw_s3, field_rw_u4)

    def test_iter(self):
        field_map = FieldMap({
            "a": Field(field.R, unsigned(1)),
            "b": Field(field.RW, signed(3))
        })
        self.assertEqual(list(field_map.items()), [
            ("a", field_map["a"]),
            ("b", field_map["b"]),
        ])
        _silence_unused(*(v for k, v in field_map.flatten()))

    def test_flatten(self):
        field_map = FieldMap({
            "a": Field(field.R, unsigned(1)),
            "b": Field(field.RW, signed(3)),
            "c": {"d": Field(field.RW, unsigned(4))},
        })
        self.assertEqual(list(field_map.flatten()), [
            (("a",), field_map["a"]),
            (("b",), field_map["b"]),
            (("c", "d"), field_map["c"]["d"]),
        ])
        _silence_unused(*(v for k, v in field_map.flatten()))

    def test_wrong_dict(self):
        with self.assertRaisesRegex(TypeError,
                r"Fields must be provided as a non-empty dict, not 'foo'"):
            FieldMap("foo")

    def test_wrong_field_key(self):
        with self.assertRaisesRegex(TypeError,
                r"Field name must be a non-empty string, not 1"):
            FieldMap({1: Field(field.RW, unsigned(1))})
        with self.assertRaisesRegex(TypeError,
                r"Field name must be a non-empty string, not ''"):
            FieldMap({"": Field(field.RW, unsigned(1))})

    def test_wrong_field_value(self):
        with self.assertRaisesRegex(TypeError,
                r"unsigned\(1\) must be a Field object or a collection of Field objects"):
            FieldMap({"a": unsigned(1)})

    def test_getitem_wrong_key(self):
        field_map = FieldMap({"a": Field(field.RW, unsigned(1))})
        with self.assertRaises(KeyError):
            field_map["b"]
        _silence_unused(*(v for k, v in field_map.flatten()))

    def test_getitem_reserved(self):
        field_map = FieldMap({"_reserved": Field(field.RW, unsigned(1))})
        field_rw_u1 = Field(field.RW, unsigned(1)).create()
        self.assertTrue(_compatible_fields(field_map["_reserved"], field_rw_u1))
        _silence_unused(*(v for k, v in field_map.flatten()))
        _silence_unused(field_rw_u1)

    def test_getattr_missing(self):
        field_map = FieldMap({"a": Field(field.RW, unsigned(1)),
                              "b": Field(field.RW, unsigned(1))})
        with self.assertRaisesRegex(AttributeError,
                r"Field map does not have a field 'c'; did you mean one of: 'a', 'b'?"):
            field_map.c
        _silence_unused(*(v for k, v in field_map.flatten()))

    def test_getattr_reserved(self):
        field_map = FieldMap({"_reserved": Field(field.RW, unsigned(1))})
        with self.assertRaisesRegex(AttributeError,
                r"Field map field '_reserved' has a reserved name and may only be accessed by "
                r"indexing"):
            field_map._reserved
        _silence_unused(*(v for k, v in field_map.flatten()))


class FieldArrayTestCase(unittest.TestCase):
    def test_simple(self):
        field_array = FieldArray([Field(field.RW, unsigned(2)) for _ in range(8)])
        field_rw_u2 = Field(field.RW, unsigned(2)).create()
        self.assertEqual(len(field_array), 8)
        for i in range(8):
            self.assertTrue(_compatible_fields(field_array[i], field_rw_u2))
        _silence_unused(*(v for k, v in field_array.flatten()))
        _silence_unused(field_rw_u2)

    def test_dim_2(self):
        field_array = FieldArray([[Field(field.RW, unsigned(1)) for _ in range(4)]
                                  for _ in range(4)])
        field_rw_u1 = Field(field.RW, unsigned(1)).create()
        self.assertEqual(len(field_array), 4)
        for i in range(4):
            for j in range(4):
                self.assertTrue(_compatible_fields(field_array[i][j], field_rw_u1))
        _silence_unused(*(v for k, v in field_array.flatten()))
        _silence_unused(field_rw_u1)

    def test_nested(self):
        field_array = FieldArray([{"a": Field(field.RW, unsigned(4)),
                                   "b": [Field(field.RW, unsigned(1)) for _ in range(4)]}
                                  for _ in range(4)])
        field_rw_u4 = Field(field.RW, unsigned(4)).create()
        field_rw_u1 = Field(field.RW, unsigned(1)).create()
        self.assertEqual(len(field_array), 4)
        for i in range(4):
            self.assertTrue(_compatible_fields(field_array[i]["a"], field_rw_u4))
            for j in range(4):
                self.assertTrue(_compatible_fields(field_array[i]["b"][j], field_rw_u1))
        _silence_unused(*(v for k, v in field_array.flatten()))
        _silence_unused(field_rw_u4, field_rw_u1)

    def test_iter(self):
        field_array = FieldArray([Field(field.RW, 1) for _ in range(3)])
        self.assertEqual(list(field_array), [
            field_array[i] for i in range(3)
        ])
        _silence_unused(*(v for k, v in field_array.flatten()))

    def test_flatten(self):
        field_array = FieldArray([{"a": Field(field.RW, 4),
                                   "b": [Field(field.RW, 1) for _ in range(2)]}
                                  for _ in range(2)])
        self.assertEqual(list(field_array.flatten()), [
            ((0, "a"), field_array[0]["a"]),
            ((0, "b", 0), field_array[0]["b"][0]),
            ((0, "b", 1), field_array[0]["b"][1]),
            ((1, "a"), field_array[1]["a"]),
            ((1, "b", 0), field_array[1]["b"][0]),
            ((1, "b", 1), field_array[1]["b"][1]),
        ])
        _silence_unused(*(v for k, v in field_array.flatten()))

    def test_wrong_fields(self):
        with self.assertRaisesRegex(TypeError,
                r"Fields must be provided as a non-empty list, not 'foo'"):
            FieldArray("foo")
        with self.assertRaisesRegex(TypeError,
                r"Fields must be provided as a non-empty list, not \[\]"):
            FieldArray([])

    def test_wrong_field(self):
        with self.assertRaisesRegex(TypeError,
                r"'foo' must be a Field object or a collection of Field objects"):
            FieldArray(["foo", Field(field.RW, 1)])


class RegisterTestCase(unittest.TestCase):
    def test_fields_dict(self):
        reg = Register("rw", {
            "a": Field(field.R, unsigned(1)),
            "b": Field(field.RW1C, unsigned(3)),
            "c": {"d": Field(field.RW, signed(2))},
            "e": [Field(field.W, unsigned(1)) for _ in range(2)]
        })

        field_r_u1    = Field(field.R,    unsigned(1)).create()
        field_rw1c_u3 = Field(field.RW1C, unsigned(3)).create()
        field_rw_s2   = Field(field.RW,     signed(2)).create()
        field_w_u1    = Field(field.W,    unsigned(1)).create()

        self.assertTrue(_compatible_fields(reg.f.a,    field_r_u1))
        self.assertTrue(_compatible_fields(reg.f.b,    field_rw1c_u3))
        self.assertTrue(_compatible_fields(reg.f.c.d,  field_rw_s2))
        self.assertTrue(_compatible_fields(reg.f.e[0], field_w_u1))
        self.assertTrue(_compatible_fields(reg.f.e[1], field_w_u1))

        self.assertEqual(reg.access, Element.Access.RW)
        self.assertEqual(reg.element.width, 8)
        self.assertEqual(reg.element.access.readable(), True)
        self.assertEqual(reg.element.access.writable(), True)

        _silence_unused(reg, field_r_u1, field_rw1c_u3, field_rw_s2, field_w_u1)

    def test_fields_list(self):
        reg = Register(access="r", fields=[
            {"a": Field(field.R, unsigned(1))} for _ in range(2)
        ])

        field_r_u1 = Field(field.R, unsigned(1)).create()

        self.assertTrue(_compatible_fields(reg.f[0].a, field_r_u1))
        self.assertTrue(_compatible_fields(reg.f[1].a, field_r_u1))

        self.assertEqual(reg.access, Element.Access.R)
        self.assertEqual(reg.element.width, 2)
        self.assertEqual(reg.element.access.readable(), True)
        self.assertEqual(reg.element.access.writable(), False)

        _silence_unused(reg, field_r_u1)

    def test_wrong_fields(self):
        with self.assertRaisesRegex(TypeError,
                r"Field collection must be a dict or a list, not 'foo'"):
            Register(access="rw", fields="foo")

    def test_annotations(self):
        class MockRegister(Register):
            a: Field(field.R, unsigned(1))
            b: {"c": Field(field.RW1C, unsigned(3)),
                "d": [Field(field.W, unsigned(1)) for _ in range(2)]}
            e: [{"f": Field(field.RW, signed(2))} for _ in range(2)] + [
                [Field(field.RW, signed(2))]]
            g: {"x": "foo", "y": dict(), "z": "bar"}
            h: ["foo", [], dict()]

            foo: unsigned(42)

        reg = MockRegister("rw")

        field_r_u1    = Field(field.R,    unsigned(1)).create()
        field_rw1c_u3 = Field(field.RW1C, unsigned(3)).create()
        field_w_u1    = Field(field.W,    unsigned(1)).create()
        field_rw_s2   = Field(field.RW,     signed(2)).create()

        self.assertTrue(_compatible_fields(reg.f.a,       field_r_u1))
        self.assertTrue(_compatible_fields(reg.f.b.c,     field_rw1c_u3))
        self.assertTrue(_compatible_fields(reg.f.b.d[0],  field_w_u1))
        self.assertTrue(_compatible_fields(reg.f.b.d[1],  field_w_u1))
        self.assertTrue(_compatible_fields(reg.f.e[0].f,  field_rw_s2))
        self.assertTrue(_compatible_fields(reg.f.e[1].f,  field_rw_s2))
        self.assertTrue(_compatible_fields(reg.f.e[2][0], field_rw_s2))

        self.assertEqual(reg.element.width, 12)
        self.assertEqual(reg.element.access.readable(), True)
        self.assertEqual(reg.element.access.writable(), True)

        _silence_unused(reg, field_r_u1, field_rw1c_u3, field_w_u1, field_rw_s2)

    def test_annotations_conflict(self):
        class MockRegister(Register):
            a: Field(field.R, unsigned(1))
        with self.assertRaisesRegex(ValueError,
                r"Field collection \{'b': <.*>\} cannot be provided in addition to field "
                r"annotations: a"):
            MockRegister("rw", {"b": Field(field.W, unsigned(1))})

    def test_annotations_other(self):
        class MockRegister(Register):
            foo: "bar"
        reg = MockRegister("rw", {"a": Field(field.R, unsigned(1))})
        field_r_u1 = Field(field.R, unsigned(1)).create()
        self.assertTrue(_compatible_fields(reg.f.a, field_r_u1))
        self.assertEqual(reg.element.width, 1)
        _silence_unused(reg, field_r_u1)

    def test_wrong_access(self):
        with self.assertRaisesRegex(TypeError,
                r"Access mode must be one of \"r\", \"w\", or \"rw\", not 'foo'"):
            Register(access="foo")

    def test_access_mismatch(self):
        class _UnusedField(Field):
            def create(self):
                obj = super().create()
                _silence_unused(obj)
                return obj
        with self.assertRaisesRegex(ValueError,
                r"Field a__b is readable, but register access mode is \<Access\.W: 'w'\>"):
            Register("w", {"a": {"b": _UnusedField(field.RW, unsigned(1))}})
        with self.assertRaisesRegex(ValueError,
                r"Field a__b is writable, but register access mode is \<Access\.R: 'r'\>"):
            Register("r", {"a": {"b": _UnusedField(field.RW, unsigned(1))}})

    def test_iter(self):
        reg = Register("rw", {
            "a": Field(field.R, unsigned(1)),
            "b": Field(field.RW1C, unsigned(3)),
            "c": {"d": Field(field.RW, signed(2))},
            "e": [Field(field.W, unsigned(1)) for _ in range(2)]
        })
        self.assertEqual(list(reg), [
            (("a",), reg.f.a),
            (("b",), reg.f.b),
            (("c", "d"), reg.f.c.d),
            (("e", 0), reg.f.e[0]),
            (("e", 1), reg.f.e[1]),
        ])
        _silence_unused(reg)

    def test_sim(self):
        dut = Register("rw", {
            "a": Field(field.R, unsigned(1)),
            "b": Field(field.RW1C, unsigned(3), reset=0b111),
            "c": {"d": Field(field.RW, signed(2), reset=-1)},
            "e": [Field(field.W, unsigned(1)) for _ in range(2)],
            "f": Field(field.RW1S, unsigned(3)),
        })

        def process():
            # Check reset values:

            self.assertEqual((yield dut.f.b  .data),  0b111)
            self.assertEqual((yield dut.f.c.d.data), -1)
            self.assertEqual((yield dut.f.f  .data),  0b000)

            self.assertEqual((yield dut.f.b   .port.r_data),  0b111)
            self.assertEqual((yield dut.f.c.d .port.r_data), -1)
            self.assertEqual((yield dut.f.f   .port.r_data),  0b000)

            # Initiator read:

            yield dut.element.r_stb.eq(1)
            yield Delay()

            self.assertEqual((yield dut.f.a.port.r_stb), 1)
            self.assertEqual((yield dut.f.b.port.r_stb), 1)
            self.assertEqual((yield dut.f.f.port.r_stb), 1)

            yield dut.element.r_stb.eq(0)

            # Initiator write:

            yield dut.element.w_stb .eq(1)
            yield dut.element.w_data.eq(Cat(
                Const(0b1,   1), # a
                Const(0b010, 3), # b
                Const(0b00,  2), # c.d
                Const(0b00,  2), # e
                Const(0b110, 3), # f
            ))
            yield Settle()

            self.assertEqual((yield dut.f.a   .port.w_stb), 0)
            self.assertEqual((yield dut.f.b   .port.w_stb), 1)
            self.assertEqual((yield dut.f.c.d .port.w_stb), 1)
            self.assertEqual((yield dut.f.e[0].port.w_stb), 1)
            self.assertEqual((yield dut.f.e[1].port.w_stb), 1)
            self.assertEqual((yield dut.f.f   .port.w_stb), 1)

            self.assertEqual((yield dut.f.b   .port.w_data), 0b010)
            self.assertEqual((yield dut.f.c.d .port.w_data), 0b00)
            self.assertEqual((yield dut.f.e[0].port.w_data), 0b0)
            self.assertEqual((yield dut.f.e[1].port.w_data), 0b0)
            self.assertEqual((yield dut.f.f   .port.w_data), 0b110)

            self.assertEqual((yield dut.f.e[0].w_data), 0b0)
            self.assertEqual((yield dut.f.e[1].w_data), 0b0)

            yield
            yield dut.element.w_stb.eq(0)
            yield Settle()

            self.assertEqual((yield dut.f.b  .data), 0b101)
            self.assertEqual((yield dut.f.c.d.data), 0b00)
            self.assertEqual((yield dut.f.f  .data), 0b110)

            # User write:

            yield dut.f.a.r_data.eq(0b1)
            yield dut.f.b.set   .eq(0b010)
            yield dut.f.f.clear .eq(0b010)
            yield Settle()

            self.assertEqual((yield dut.element.r_data),
                             Const.cast(Cat(
                                 Const(0b1,   1), # a
                                 Const(0b101, 3), # b
                                 Const(0b00,  2), # c.d
                                 Const(0b00,  2), # e
                                 Const(0b110, 3), # f
                             )).value)

            yield
            yield dut.f.a.r_data.eq(0b0)
            yield dut.f.b.set   .eq(0b000)
            yield dut.f.f.clear .eq(0b000)
            yield Settle()

            self.assertEqual((yield dut.element.r_data),
                             Const.cast(Cat(
                                 Const(0b0,   1), # a
                                 Const(0b111, 3), # b
                                 Const(0b00,  2), # c.d
                                 Const(0b00,  2), # e
                                 Const(0b100, 3), # f
                             )).value)

            # Concurrent writes:

            yield dut.element.w_stb .eq(1)
            yield dut.element.w_data.eq(Cat(
                Const(0b0,   1), # a
                Const(0b111, 3), # b
                Const(0b00,  2), # c.d
                Const(0b00,  2), # e
                Const(0b111, 3), # f
            ))

            yield dut.f.b.set  .eq(0b001)
            yield dut.f.f.clear.eq(0b111)
            yield
            yield Settle()

            self.assertEqual((yield dut.element.r_data),
                             Const.cast(Cat(
                                 Const(0b0,   1), # a
                                 Const(0b001, 3), # b
                                 Const(0b00,  2), # c.d
                                 Const(0b00,  2), # e
                                 Const(0b111, 3), # f
                             )).value)

            self.assertEqual((yield dut.f.b.data), 0b001)
            self.assertEqual((yield dut.f.f.data), 0b111)

        sim = Simulator(dut)
        sim.add_clock(1e-6)
        sim.add_sync_process(process)
        with sim.write_vcd(vcd_file=open("test.vcd", "w")):
            sim.run()


class RegisterMapTestCase(unittest.TestCase):
    def setUp(self):
        self.map = RegisterMap()

    def test_add_register(self):
        reg_rw_a = Register("rw", {"a": Field(field.RW, 1)})
        self.assertIs(self.map.add_register(reg_rw_a, name="reg_rw_a"), reg_rw_a)
        _silence_unused(reg_rw_a)

    def test_add_register_frozen(self):
        self.map.freeze()
        reg_rw_a = Register("rw", {"a": Field(field.RW, 1)})
        with self.assertRaisesRegex(ValueError, r"Register map is frozen"):
            self.map.add_register(reg_rw_a, name="reg_rw_a")
        _silence_unused(reg_rw_a)

    def test_add_register_wrong_type(self):
        with self.assertRaisesRegex(TypeError,
                r"Register must be an instance of csr\.Register, not 'foo'"):
            self.map.add_register("foo", name="foo")

    def test_add_register_wrong_name(self):
        reg_rw_a = Register("rw", {"a": Field(field.RW, 1)})
        with self.assertRaisesRegex(TypeError,
                r"Name must be a non-empty string, not None"):
            self.map.add_register(reg_rw_a, name=None)
        _silence_unused(reg_rw_a)

    def test_add_register_empty_name(self):
        reg_rw_a = Register("rw", {"a": Field(field.RW, 1)})
        with self.assertRaisesRegex(TypeError,
                r"Name must be a non-empty string, not ''"):
            self.map.add_register(reg_rw_a, name="")
        _silence_unused(reg_rw_a)

    def test_add_cluster(self):
        cluster = RegisterMap()
        self.assertIs(self.map.add_cluster(cluster, name="cluster"), cluster)

    def test_add_cluster_frozen(self):
        self.map.freeze()
        cluster = RegisterMap()
        with self.assertRaisesRegex(ValueError, r"Register map is frozen"):
            self.map.add_cluster(cluster, name="cluster")

    def test_add_cluster_wrong_type(self):
        with self.assertRaisesRegex(TypeError,
                r"Cluster must be an instance of csr\.RegisterMap, not 'foo'"):
            self.map.add_cluster("foo", name="foo")

    def test_add_cluster_wrong_name(self):
        cluster = RegisterMap()
        with self.assertRaisesRegex(TypeError,
                r"Name must be a non-empty string, not None"):
            self.map.add_cluster(cluster, name=None)

    def test_add_cluster_empty_name(self):
        cluster = RegisterMap()
        with self.assertRaisesRegex(TypeError,
                r"Name must be a non-empty string, not ''"):
            self.map.add_cluster(cluster, name="")

    def test_namespace_collision(self):
        reg_rw_a  = Register("rw", {"a": Field(field.RW, 1)})
        reg_rw_b  = Register("rw", {"b": Field(field.RW, 1)})
        cluster_0 = RegisterMap()
        cluster_1 = RegisterMap()

        self.map.add_register(reg_rw_a, name="reg_rw_a")
        self.map.add_cluster(cluster_0, name="cluster_0")

        with self.assertRaisesRegex(ValueError, # register/register
                r"Name 'reg_rw_a' is already used by *"):
            self.map.add_register(reg_rw_b, name="reg_rw_a")
        with self.assertRaisesRegex(ValueError, # register/cluster
                r"Name 'reg_rw_a' is already used by *"):
            self.map.add_cluster(cluster_1, name="reg_rw_a")
        with self.assertRaisesRegex(ValueError, # cluster/cluster
                r"Name 'cluster_0' is already used by *"):
            self.map.add_cluster(cluster_1, name="cluster_0")
        with self.assertRaisesRegex(ValueError, # cluster/register
                r"Name 'cluster_0' is already used by *"):
            self.map.add_register(reg_rw_b, name="cluster_0")

        _silence_unused(reg_rw_a, reg_rw_b)

    def test_iter_registers(self):
        reg_rw_a = Register("rw", {"a": Field(field.RW, 1)})
        reg_rw_b = Register("rw", {"b": Field(field.RW, 1)})
        self.map.add_register(reg_rw_a, name="reg_rw_a")
        self.map.add_register(reg_rw_b, name="reg_rw_b")

        registers = list(self.map.registers())

        self.assertEqual(len(registers), 2)
        self.assertIs(registers[0][0], reg_rw_a)
        self.assertEqual(registers[0][1], "reg_rw_a")
        self.assertIs(registers[1][0], reg_rw_b)
        self.assertEqual(registers[1][1], "reg_rw_b")

        _silence_unused(reg_rw_a, reg_rw_b)

    def test_iter_clusters(self):
        cluster_0 = RegisterMap()
        cluster_1 = RegisterMap()
        self.map.add_cluster(cluster_0, name="cluster_0")
        self.map.add_cluster(cluster_1, name="cluster_1")

        clusters = list(self.map.clusters())

        self.assertEqual(len(clusters), 2)
        self.assertIs(clusters[0][0], cluster_0)
        self.assertEqual(clusters[0][1], "cluster_0")
        self.assertIs(clusters[1][0], cluster_1)
        self.assertEqual(clusters[1][1], "cluster_1")

    def test_iter_flatten(self):
        reg_rw_a  = Register("rw", {"a": Field(field.RW, 1)})
        reg_rw_b  = Register("rw", {"b": Field(field.RW, 1)})
        cluster_0 = RegisterMap()
        cluster_1 = RegisterMap()

        cluster_0.add_register(reg_rw_a, name="reg_rw_a")
        cluster_1.add_register(reg_rw_b, name="reg_rw_b")

        self.map.add_cluster(cluster_0, name="cluster_0")
        self.map.add_cluster(cluster_1, name="cluster_1")

        registers = list(self.map.flatten())

        self.assertEqual(len(registers), 2)
        self.assertIs(registers[0][0], reg_rw_a)
        self.assertEqual(registers[0][1], ("cluster_0", "reg_rw_a"))
        self.assertIs(registers[1][0], reg_rw_b)
        self.assertEqual(registers[1][1], ("cluster_1", "reg_rw_b"))

        _silence_unused(reg_rw_a, reg_rw_b)

    def test_get_path(self):
        reg_rw_a = Register("rw", {"a": Field(field.RW, 1)})
        reg_rw_b = Register("rw", {"b": Field(field.RW, 1)})
        reg_rw_c = Register("rw", {"c": Field(field.RW, 1)})

        cluster_0 = RegisterMap()
        cluster_0.add_register(reg_rw_a, name="reg_rw_a")

        cluster_1 = RegisterMap()
        cluster_1.add_register(reg_rw_c, name="reg_rw_c")

        self.map.add_cluster(cluster_0, name="cluster_0")
        self.map.add_register(reg_rw_b, name="reg_rw_b")
        self.map.add_cluster(cluster_1, name="cluster_1")

        self.assertEqual(self.map.get_path(reg_rw_a), ("cluster_0", "reg_rw_a"))
        self.assertEqual(self.map.get_path(reg_rw_b), ("reg_rw_b",))
        self.assertEqual(self.map.get_path(reg_rw_c), ("cluster_1", "reg_rw_c"))

        _silence_unused(reg_rw_a, reg_rw_b, reg_rw_c)

    def test_get_path_wrong_register(self):
        with self.assertRaisesRegex(TypeError,
                r"Register must be an instance of csr\.Register, not 'foo'"):
            self.map.get_path("foo")

    def test_get_path_unknown_register(self):
        reg_rw_a = Register("rw", {"a": Field(field.RW, 1)})
        with self.assertRaises(KeyError):
            self.map.get_path(reg_rw_a)
        _silence_unused(reg_rw_a)

    def test_get_register(self):
        reg_rw_a  = Register("rw", {"a": Field(field.RW, 1)})
        reg_rw_b  = Register("rw", {"b": Field(field.RW, 1)})
        cluster_0 = RegisterMap()

        cluster_0.add_register(reg_rw_a, name="reg_rw_a")
        self.map.add_cluster(cluster_0, name="cluster_0")
        self.map.add_register(reg_rw_b, name="reg_rw_b")

        self.assertIs(self.map.get_register(("cluster_0", "reg_rw_a")), reg_rw_a)
        self.assertIs(self.map.get_register(("reg_rw_b",)), reg_rw_b)

        _silence_unused(reg_rw_a, reg_rw_b)

    def test_get_register_empty_path(self):
        with self.assertRaisesRegex(ValueError, r"Path must be a non-empty iterable"):
            self.map.get_register(())

    def test_get_register_wrong_path(self):
        with self.assertRaisesRegex(TypeError,
                r"Path must contain non-empty strings, not 0"):
            self.map.get_register(("cluster_0", 0))
        with self.assertRaisesRegex(TypeError,
                r"Path must contain non-empty strings, not ''"):
            self.map.get_register(("", "reg_rw_a"))

    def test_get_register_unknown_path(self):
        self.map.add_cluster(RegisterMap(), name="cluster_0")
        with self.assertRaises(KeyError):
            self.map.get_register(("reg_rw_a",))
        with self.assertRaises(KeyError):
            self.map.get_register(("cluster_0", "reg_rw_a"))


class BridgeTestCase(unittest.TestCase):
    def test_memory_map(self):
        reg_rw_4  = Register("rw", {"a": Field(field.RW,  4)})
        reg_rw_8  = Register("rw", {"a": Field(field.RW,  8)})
        reg_rw_12 = Register("rw", {"a": Field(field.RW, 12)})
        reg_rw_16 = Register("rw", {"a": Field(field.RW, 16)})

        cluster_0 = RegisterMap()
        cluster_0.add_register(reg_rw_12, name="reg_rw_12")
        cluster_0.add_register(reg_rw_16, name="reg_rw_16")

        register_map = RegisterMap()
        register_map.add_register(reg_rw_4, name="reg_rw_4")
        register_map.add_register(reg_rw_8, name="reg_rw_8")
        register_map.add_cluster(cluster_0, name="cluster_0")

        dut = Bridge(register_map, addr_width=16, data_width=8)
        registers = list(dut.bus.memory_map.resources())

        self.assertIs(registers[0][0], reg_rw_4.element)
        self.assertEqual(registers[0][1], "reg_rw_4")
        self.assertEqual(registers[0][2], (0, 1))

        self.assertIs(registers[1][0], reg_rw_8.element)
        self.assertEqual(registers[1][1], "reg_rw_8")
        self.assertEqual(registers[1][2], (1, 2))

        self.assertIs(registers[2][0], reg_rw_12.element)
        self.assertEqual(registers[2][1], "cluster_0__reg_rw_12")
        self.assertEqual(registers[2][2], (2, 4))

        self.assertIs(registers[3][0], reg_rw_16.element)
        self.assertEqual(registers[3][1], "cluster_0__reg_rw_16")
        self.assertEqual(registers[3][2], (4, 6))

        _silence_unused(dut)

    def test_wrong_register_map(self):
        with self.assertRaisesRegex(TypeError,
                r"Register map must be an instance of RegisterMap, not 'foo'"):
            dut = Bridge("foo", addr_width=16, data_width=8)

    def test_register_addr(self):
        reg_rw_4  = Register("rw", {"a": Field(field.RW,  4)})
        reg_rw_8  = Register("rw", {"a": Field(field.RW,  8)})
        reg_rw_12 = Register("rw", {"a": Field(field.RW, 12)})
        reg_rw_16 = Register("rw", {"a": Field(field.RW, 16)})

        cluster_0 = RegisterMap()
        cluster_0.add_register(reg_rw_12, name="reg_rw_12")
        cluster_0.add_register(reg_rw_16, name="reg_rw_16")

        register_map = RegisterMap()
        register_map.add_register(reg_rw_4, name="reg_rw_4")
        register_map.add_register(reg_rw_8, name="reg_rw_8")
        register_map.add_cluster(cluster_0, name="cluster_0")

        register_addr = {
            "reg_rw_4": 0x10,
            "reg_rw_8": None,
            "cluster_0": {
                "reg_rw_12": 0x20,
                "reg_rw_16": None,
            },
        }

        dut = Bridge(register_map, addr_width=16, data_width=8,
                     register_addr=register_addr)
        registers = list(dut.bus.memory_map.resources())

        self.assertEqual(registers[0][1], "reg_rw_4")
        self.assertEqual(registers[0][2], (0x10, 0x11))

        self.assertEqual(registers[1][1], "reg_rw_8")
        self.assertEqual(registers[1][2], (0x11, 0x12))

        self.assertEqual(registers[2][1], "cluster_0__reg_rw_12")
        self.assertEqual(registers[2][2], (0x20, 0x22))

        self.assertEqual(registers[3][1], "cluster_0__reg_rw_16")
        self.assertEqual(registers[3][2], (0x22, 0x24))

        _silence_unused(dut)

    def test_register_alignment(self):
        reg_rw_4  = Register("rw", {"a": Field(field.RW,  4)})
        reg_rw_8  = Register("rw", {"a": Field(field.RW,  8)})
        reg_rw_12 = Register("rw", {"a": Field(field.RW, 12)})
        reg_rw_16 = Register("rw", {"a": Field(field.RW, 16)})

        cluster_0 = RegisterMap()
        cluster_0.add_register(reg_rw_12, name="reg_rw_12")
        cluster_0.add_register(reg_rw_16, name="reg_rw_16")

        register_map = RegisterMap()
        register_map.add_register(reg_rw_4, name="reg_rw_4")
        register_map.add_register(reg_rw_8, name="reg_rw_8")
        register_map.add_cluster(cluster_0, name="cluster_0")

        register_alignment = {
            "reg_rw_4": None,
            "reg_rw_8": None,
            "cluster_0": {
                "reg_rw_12": 3,
                "reg_rw_16": None,
            },
        }

        dut = Bridge(register_map, addr_width=16, data_width=8, alignment=1,
                     register_alignment=register_alignment)
        registers = list(dut.bus.memory_map.resources())

        self.assertEqual(registers[0][1], "reg_rw_4")
        self.assertEqual(registers[0][2], (0, 2))

        self.assertEqual(registers[1][1], "reg_rw_8")
        self.assertEqual(registers[1][2], (2, 4)),

        self.assertEqual(registers[2][1], "cluster_0__reg_rw_12")
        self.assertEqual(registers[2][2], (8, 16))

        self.assertEqual(registers[3][1], "cluster_0__reg_rw_16")
        self.assertEqual(registers[3][2], (16, 18))

        _silence_unused(dut)

    def test_register_out_of_bounds(self):
        reg_rw_24 = Register("rw", {"a": Field(field.RW, 24)})
        register_map = RegisterMap()
        register_map.add_register(reg_rw_24, name="reg_rw_24")
        with self.assertRaisesRegex(ValueError,
                r"Address range 0x0\.\.0x3 out of bounds for memory map spanning "
                r"range 0x0\.\.0x2 \(1 address bits\)"):
            dut = Bridge(register_map, addr_width=1, data_width=8)
        _silence_unused(reg_rw_24)

    def test_wrong_register_address(self):
        reg_rw_4 = Register("rw", {"a": Field(field.RW, 4)})
        register_map = RegisterMap()
        register_map.add_register(reg_rw_4, name="reg_rw_4")
        with self.assertRaisesRegex(TypeError, r"Register address must be a dict, not 'foo'"):
            dut = Bridge(register_map, addr_width=1, data_width=8, register_addr="foo")
        _silence_unused(reg_rw_4)

    def test_wrong_cluster_address(self):
        reg_rw_4  = Register("rw", {"a": Field(field.RW, 4)})
        cluster_0 = RegisterMap()
        cluster_0.add_register(reg_rw_4, name="reg_rw_4")
        register_map = RegisterMap()
        register_map.add_cluster(cluster_0, name="cluster_0")
        with self.assertRaisesRegex(TypeError,
                r"Register address \('cluster_0',\) must be a dict, not 'foo'"):
            dut = Bridge(register_map, addr_width=1, data_width=8,
                         register_addr={"cluster_0": "foo"})
        _silence_unused(reg_rw_4)

    def test_wrong_register_alignment(self):
        reg_rw_4 = Register("rw", {"a": Field(field.RW, 4)})
        register_map = RegisterMap()
        register_map.add_register(reg_rw_4, name="reg_rw_4")
        with self.assertRaisesRegex(TypeError, r"Register alignment must be a dict, not 'foo'"):
            dut = Bridge(register_map, addr_width=1, data_width=8, register_alignment="foo")
        _silence_unused(reg_rw_4)

    def test_wrong_cluster_alignment(self):
        reg_rw_4  = Register("rw", {"a": Field(field.RW, 4)})
        cluster_0 = RegisterMap()
        cluster_0.add_register(reg_rw_4, name="reg_rw_4")
        register_map = RegisterMap()
        register_map.add_cluster(cluster_0, name="cluster_0")
        with self.assertRaisesRegex(TypeError,
                r"Register alignment \('cluster_0',\) must be a dict, not 'foo'"):
            dut = Bridge(register_map, addr_width=1, data_width=8,
                         register_alignment={"cluster_0": "foo"})
        _silence_unused(reg_rw_4)

    def test_sim(self):
        reg_rw_4  = Register("rw", {"a": Field(field.RW,  4, reset=0x0)})
        reg_rw_8  = Register("rw", {"a": Field(field.RW,  8, reset=0x11)})
        reg_rw_16 = Register("rw", {"a": Field(field.RW, 16, reset=0x3322)})

        cluster_0 = RegisterMap()
        cluster_0.add_register(reg_rw_16, name="reg_rw_16")

        register_map = RegisterMap()
        register_map.add_register(reg_rw_4, name="reg_rw_4")
        register_map.add_register(reg_rw_8, name="reg_rw_8")
        register_map.add_cluster(cluster_0, name="cluster_0")

        dut = Bridge(register_map, addr_width=16, data_width=8)

        def process():
            yield dut.bus.addr.eq(0)
            yield dut.bus.r_stb.eq(1)
            yield dut.bus.w_stb.eq(1)
            yield dut.bus.w_data.eq(0xa)
            yield
            yield Settle()
            self.assertEqual((yield dut.bus.r_data), 0x0)
            self.assertEqual((yield reg_rw_4 .f.a.port.r_stb), 1)
            self.assertEqual((yield reg_rw_8 .f.a.port.r_stb), 0)
            self.assertEqual((yield reg_rw_16.f.a.port.r_stb), 0)
            self.assertEqual((yield reg_rw_4 .f.a.port.w_stb), 1)
            self.assertEqual((yield reg_rw_8 .f.a.port.w_stb), 0)
            self.assertEqual((yield reg_rw_16.f.a.port.w_stb), 0)
            yield dut.bus.r_stb.eq(0)
            yield dut.bus.w_stb.eq(0)
            yield
            yield Settle()
            self.assertEqual((yield reg_rw_4.f.a.data), 0xa)

            yield dut.bus.addr.eq(1)
            yield dut.bus.r_stb.eq(1)
            yield dut.bus.w_stb.eq(1)
            yield dut.bus.w_data.eq(0xbb)
            yield
            yield Settle()
            self.assertEqual((yield dut.bus.r_data), 0x11)
            self.assertEqual((yield reg_rw_4 .f.a.port.r_stb), 0)
            self.assertEqual((yield reg_rw_8 .f.a.port.r_stb), 1)
            self.assertEqual((yield reg_rw_16.f.a.port.r_stb), 0)
            self.assertEqual((yield reg_rw_4 .f.a.port.w_stb), 0)
            self.assertEqual((yield reg_rw_8 .f.a.port.w_stb), 1)
            self.assertEqual((yield reg_rw_16.f.a.port.w_stb), 0)
            yield dut.bus.r_stb.eq(0)
            yield dut.bus.w_stb.eq(0)
            yield
            yield Settle()
            self.assertEqual((yield reg_rw_8.f.a.data), 0xbb)

            yield dut.bus.addr.eq(2)
            yield dut.bus.r_stb.eq(1)
            yield dut.bus.w_stb.eq(1)
            yield dut.bus.w_data.eq(0xcc)
            yield
            yield Settle()
            self.assertEqual((yield dut.bus.r_data), 0x22)
            self.assertEqual((yield reg_rw_4 .f.a.port.r_stb), 0)
            self.assertEqual((yield reg_rw_8 .f.a.port.r_stb), 0)
            self.assertEqual((yield reg_rw_16.f.a.port.r_stb), 1)
            self.assertEqual((yield reg_rw_4 .f.a.port.w_stb), 0)
            self.assertEqual((yield reg_rw_8 .f.a.port.w_stb), 0)
            self.assertEqual((yield reg_rw_16.f.a.port.w_stb), 0)
            yield dut.bus.r_stb.eq(0)
            yield dut.bus.w_stb.eq(0)
            yield
            yield Settle()
            self.assertEqual((yield reg_rw_16.f.a.data), 0x3322)

            yield dut.bus.addr.eq(3)
            yield dut.bus.r_stb.eq(1)
            yield dut.bus.w_stb.eq(1)
            yield dut.bus.w_data.eq(0xdd)
            yield
            yield Settle()
            self.assertEqual((yield dut.bus.r_data), 0x33)
            self.assertEqual((yield reg_rw_4 .f.a.port.r_stb), 0)
            self.assertEqual((yield reg_rw_8 .f.a.port.r_stb), 0)
            self.assertEqual((yield reg_rw_16.f.a.port.r_stb), 0)
            self.assertEqual((yield reg_rw_4 .f.a.port.w_stb), 0)
            self.assertEqual((yield reg_rw_8 .f.a.port.w_stb), 0)
            self.assertEqual((yield reg_rw_16.f.a.port.w_stb), 1)
            yield dut.bus.r_stb.eq(0)
            yield dut.bus.w_stb.eq(0)
            yield
            yield Settle()
            self.assertEqual((yield reg_rw_16.f.a.data), 0xddcc)

        sim = Simulator(dut)
        sim.add_clock(1e-6)
        sim.add_sync_process(process)
        with sim.write_vcd(vcd_file=open("test.vcd", "w")):
            sim.run()
