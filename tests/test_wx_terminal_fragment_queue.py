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


def test_fragment_queue_clears_inflight_and_sensitive_payload_on_reset():
    queue = TerminalFragmentQueue()
    assert queue.enqueue("hpcWrite", "sensitive-output")
    assert queue.start_next() is not None
    queue.reset()

    assert queue.inflight is None
    assert queue.queued_entries == 0
    assert queue.queued_bytes == 0
