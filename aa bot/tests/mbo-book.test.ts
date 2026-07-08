import { describe, expect, it } from "vitest";
import { MboBook } from "../server/core/mbo-book";

describe("MboBook", () => {
  it("reconstructs and updates a Level 3 book by order id", () => {
    const book = new MboBook();
    book.loadLevel3({ sequence: 100, bids: [["100", "2", "b1"]], asks: [["101", "3", "a1"]] });
    expect(book.top(1).bids[0]).toMatchObject({ price: 100, size: 2, orders: 1 });

    expect(book.apply({ type: "open", sequence: 101, order_id: "b2", side: "buy", price: "100", remaining_size: "1" }).gap).toBe(false);
    expect(book.top(1).bids[0]).toMatchObject({ size: 3, orders: 2 });

    book.apply({ type: "match", sequence: 102, maker_order_id: "b1", side: "buy", price: "100", size: "0.5" });
    expect(book.top(1).bids[0]?.size).toBe(2.5);

    book.apply({ type: "done", sequence: 103, order_id: "a1", side: "sell", price: "101" });
    expect(book.top(1).asks).toHaveLength(0);
  });

  it("detects sequence gaps and refuses the unsafe update", () => {
    const book = new MboBook();
    book.loadLevel3({ sequence: 10, bids: [["100", "1", "b1"]], asks: [] });
    const result = book.apply({ type: "done", sequence: 12, order_id: "b1" });
    expect(result.gap).toBe(true);
    expect(book.sequence).toBe(10);
    expect(book.orderCount).toBe(1);
  });
});
