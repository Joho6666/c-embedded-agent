FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_GATEWAY_ADMIN_API=http://localhost:8000
ARG NEXT_PUBLIC_ADMIN_API_KEY=gw-admin-dev-key
ARG NEXT_PUBLIC_GATEWAY_PUBLIC_URL=http://localhost:8000/v1
ENV NEXT_PUBLIC_GATEWAY_ADMIN_API=$NEXT_PUBLIC_GATEWAY_ADMIN_API
ENV NEXT_PUBLIC_ADMIN_API_KEY=$NEXT_PUBLIC_ADMIN_API_KEY
ENV NEXT_PUBLIC_GATEWAY_PUBLIC_URL=$NEXT_PUBLIC_GATEWAY_PUBLIC_URL
RUN npm run build

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next ./.next
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["npm", "start"]
