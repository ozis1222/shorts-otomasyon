/**
 * Order source abstraction (spec §28). The engine is driven entirely through
 * this interface, so it can be developed and tested with MockOrderProvider and
 * later switched to Etsy without touching the pipeline. We never scrape or
 * bypass APIs the platform doesn't sanction.
 */
import { randomBytes } from 'node:crypto';

export interface Order {
  orderId: string;
  /** Unguessable token used in the customer's private upload/download URL. */
  secureToken: string;
  packageId: string;
  buyerEmail?: string;
  createdAt: string;
  /** ISO expiry for the secure link. */
  expiresAt: string;
}

export interface OrderProvider {
  readonly name: string;
  listNewOrders(): Promise<Order[]>;
  getOrder(orderId: string): Promise<Order | null>;
}

/** 32-byte URL-safe token — far stronger than a UUID for guess-resistance. */
export function generateSecureToken(): string {
  return randomBytes(32).toString('base64url');
}

export class MockOrderProvider implements OrderProvider {
  readonly name = 'mock';
  private orders = new Map<string, Order>();

  createDemoOrder(packageId = 'full', buyerEmail = 'demo@example.com'): Order {
    const orderId = `MOCK-${Date.now().toString(36).toUpperCase()}`;
    const order: Order = {
      orderId,
      secureToken: generateSecureToken(),
      packageId,
      buyerEmail,
      createdAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 30 * 86400000).toISOString(),
    };
    this.orders.set(orderId, order);
    return order;
  }

  async listNewOrders(): Promise<Order[]> {
    return [...this.orders.values()];
  }
  async getOrder(orderId: string): Promise<Order | null> {
    return this.orders.get(orderId) ?? null;
  }
}

/**
 * Placeholder for the real Etsy integration. Wire the official Etsy Open API v3
 * (OAuth2) here — receipts → orders — once credentials are configured. Kept as a
 * clearly-marked stub so the seam is real in code and the demo path never
 * depends on it.
 */
export class EtsyOrderProvider implements OrderProvider {
  readonly name = 'etsy';
  constructor(private readonly _apiKey: string) {}
  async listNewOrders(): Promise<Order[]> {
    throw new Error('EtsyOrderProvider not yet configured. Set ETSY_API_KEY and implement OAuth.');
  }
  async getOrder(): Promise<Order | null> {
    throw new Error('EtsyOrderProvider not yet configured.');
  }
}
