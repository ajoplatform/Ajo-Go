import pytest
from api.services.whatsapp_parser import parse_line, parse_file, WhatsAppParseResult


class TestParseLine:
    def test_paid_keyword(self):
        result = parse_line("12/03/2025, 08:30 - Chidi: paid 5000")
        assert result.amount == 5000
        assert result.sender == "Chidi"
        assert result.confidence >= 0.9

    def test_direct_amount(self):
        result = parse_line("12/03/2025, 09:15 - Mary: 3000")
        assert result.amount == 3000
        assert result.sender == "Mary"

    def test_third_person_reference(self):
        result = parse_line("12/03/2025, 14:22 - Reghie: Mary 3000")
        assert result.amount == 3000
        assert result.sender == "Mary"
        assert result.confidence == 0.7

    def test_contributed_keyword(self):
        result = parse_line("Nurse Ada: contributed N10,000")
        assert result.amount == 10000
        assert result.sender == "Nurse Ada"

    def test_transfer_keyword(self):
        result = parse_line("Emeka 💰: transferred 5,000")
        assert result.amount == 5000
        assert result.sender == "Emeka 💰"

    def test_ambiguous_amount_only(self):
        result = parse_line("5000")
        assert result.amount == 5000
        assert result.sender is None
        assert result.confidence == 0.2
        assert result.needs_review is True

    def test_empty_line(self):
        result = parse_line("")
        assert result is None

    def test_no_sender(self):
        result = parse_line("12/03/2025, 08:30 - ")
        assert result is None


class TestAmountParsing:
    def test_comma_separator(self):
        result = parse_line("Chidi: 5,000")
        assert result.amount == 5000

    def test_naira_prefix(self):
        result = parse_line("Chidi: N5000")
        assert result.amount == 5000

    def test_naira_with_kobo(self):
        result = parse_line("Chidi: N5,000.00")
        assert result.amount == 5000

    def test_short_form(self):
        result = parse_line("Chidi: 5k")
        assert result.amount == 5000

    def test_word_amount(self):
        result = parse_line("Chidi: five thousand")
        assert result.amount is None
        assert result.needs_review is True

    def test_negative_amount(self):
        result = parse_line("Chidi: -5000")
        assert result is None

    def test_zero_amount(self):
        result = parse_line("Chidi: N0")
        assert result is None


class TestFileParsing:
    def test_empty_file(self):
        results = parse_file("")
        assert results == []

    def test_bom_handling(self):
        content = "\ufeff12/03/2025, 08:30 - Chidi: paid 5000"
        results = parse_file(content)
        assert len(results) >= 1

    def test_large_file_handling(self):
        lines = [
            "12/03/2025, 08:30 - Member{}: paid 5000".format(i) for i in range(10000)
        ]
        content = "\n".join(lines)
        results = parse_file(content)
        assert len(results) == 10000
