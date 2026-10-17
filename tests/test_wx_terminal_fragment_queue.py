from __future__ import annotations

from hpc_gui.wx_terminal_fragment_queue import (
    FRAGMENT_WRITE_CHARS,
    MAX_ACK_RETRIES,
    MAX_QUEUE_BYTES,
    MAX_QUEUE_ENTRIES,
    OUTPUT_LIMIT_NOTICE,
    TerminalFragmentQueue,
)


def test_fragment_queue_preserves_unicode_write_order_and_ack_sequence():
    queue = TerminalFragmentQueue()
    text = "α界🙂" * 900

    assert queue.enqueue("hpcWrite", text)
    first = queue.start_next()
    assert first is not None
    assert first.arg == text[:FRAGMENT_WRITE_CHARS]
    assert queue.queued_entries == 2

    assert queue.acknowledge(first.seq)
    second = queue.start_next()
    assert second is not None
    assert second.seq > first.seq
    assert first.arg + second.arg == text
    assert queue.acknowledge(second.seq)
    assert queue.start_next() is None
    assert queue.queued_bytes == 0


def test_fragment_queue_retries_same_sequence_then_releases_next_command():
    queue = TerminalFragmentQueue()
    assert queue.enqueue("hpcGetScreenState")
    assert queue.enqueue("hpcClear")
    first = queue.start_next()
    assert first is not None

    for _ in range(MAX_ACK_RETRIES):
        retry, exhausted = queue.retry(first.seq)
        assert retry == first
        assert not exhausted
    retry, exhausted = queue.retry(first.seq)
    assert retry is None
    assert exhausted

    second = queue.start_next()
    assert second is not None
    assert second.method == "hpcClear"
    assert queue.acknowledge(second.seq)


def test_fragment_queue_coalesces_adjacent_small_writes_before_navigation():
    queue = TerminalFragmentQueue()
    assert queue.enqueue("hpcWrite", "\x1b[?1049h")
    assert queue.enqueue("hpcWrite", "\x1b[2J\x1b[HALT-SCREEN\r\n")

    batch = queue.start_next()
    assert batch is not None
    assert batch.seq == 2
    assert batch.arg == "\x1b[?1049h\x1b[2J\x1b[HALT-SCREEN\r\n"
    assert queue.queued_entries == 1
    assert queue.acknowledge(batch.seq)


def test_fragment_queue_never_replays_non_idempotent_terminal_write():
    queue = TerminalFragmentQueue()
    assert queue.enqueue("hpcWrite", "\x1b[?1049h")
    command = queue.start_next()
    assert command is not None

    retry, exhausted = queue.retry(command.seq)
    assert retry is None
    assert exhausted


def test_fragment_queue_ack_loss_does_not_release_wrong_sequence():
    queue = TerminalFragmentQueue()
    assert queue.enqueue("hpcWrite", "secret terminal output")
    command = queue.start_next()
    assert command is not None

    assert not queue.acknowledge(command.seq + 1)
    assert queue.inflight == command
    assert queue.acknowledge(command.seq)
    assert not queue.acknowledge(command.seq)


def test_fragment_queue_is_bounded_and_emits_visible_output_drop_notice():
    queue = TerminalFragmentQueue()
    assert not queue.enqueue("hpcWrite", "x" * (MAX_QUEUE_BYTES + 1))

    assert queue.queued_entries <= MAX_QUEUE_ENTRIES
    assert queue.queued_bytes <= MAX_QUEUE_BYTES
    notice = queue.start_next()
    assert notice is not None
    assert notice.arg == OUTPUT_LIMIT_NOTICE


def test_fragment_queue_accepts_exact_two_mibibytes_then_reports_overflow():
    queue = TerminalFragmentQueue()
    # 963 full fragments plus a 1,536-character final fragment. Each of
    # the 964 queued commands accounts for its 128-byte IPC envelope.
    exact_payload_chars = 2 * 1024 * 1024 - 964 * 128
    assert exact_payload_chars == 963 * FRAGMENT_WRITE_CHARS + 1536
    assert queue.enqueue("hpcWrite", "x" * exact_payload_chars)
    assert queue.queued_bytes == MAX_QUEUE_BYTES
    assert queue.queued_entries == 964

    # The next byte exceeds the cap. Stale queued output is replaced with a
    # bounded visible notice rather than retained past the memory limit.
    assert not queue.enqueue("hpcWrite", "x")
    assert queue.queued_entries == 1
    assert queue.queued_bytes <= MAX_QUEUE_BYTES
    assert queue.start_next().arg == OUTPUT_LIMIT_NOTICE


def test_fragment_queue_accepts_exact_entry_cap_and_rejects_next_command():
    queue = TerminalFragmentQueue()
    for _ in range(MAX_QUEUE_ENTRIES):
        assert queue.enqueue("hpcClear")

    assert queue.queued_entries == MAX_QUEUE_ENTRIES
    assert queue.queued_bytes == MAX_QUEUE_ENTRIES * 128
    assert not queue.enqueue("hpcClear")
    assert queue.queued_entries == MAX_QUEUE_ENTRIES
    assert queue.queued_bytes == MAX_QUEUE_ENTRIES * 128


def test_fragment_queue_drains_high_volume_ansi_unicode_in_order():
    queue = TerminalFragmentQueue()
    payload = ("Türkçe 日本語 🙂 \x1b[32mANSI\x1b[0m\r\n" * 16_000)

    assert queue.enqueue("hpcWrite", payload)
    assert queue.queued_entries <= MAX_QUEUE_ENTRIES
    assert queue.queued_bytes <= MAX_QUEUE_BYTES

    parts = []
    sequences = []
    while (command := queue.start_next()) is not None:
        parts.append(command.arg)
        sequences.append(command.seq)
        assert queue.acknowledge(command.seq)

    assert sequences == sorted(set(sequences))
    assert "".join(parts) == payload
    assert queue.queued_entries == 0
    assert queue.queued_bytes == 0


def test_fragment_queue_clears_inflight_and_sensitive_payload_on_reset():
    queue = TerminalFragmentQueue()
    assert queue.enqueue("hpcWrite", "sensitive-output")
    assert queue.start_next() is not None
    queue.reset()

    assert queue.inflight is None
    assert queue.queued_entries == 0
    assert queue.queued_bytes == 0
