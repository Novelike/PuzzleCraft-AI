// Shared puzzle types for consistent type definitions across the application

export interface PuzzlePiece {
  id: string
  x: number
  y: number
  width: number
  height: number
  rotation: number
  imageData: string
  correctPosition: { x: number, y: number }
  currentPosition: { x: number, y: number }
  isPlaced: boolean
  isSelected: boolean
  zIndex: number
  connectedPieces: string[]
  edges: {
    top: 'flat' | 'tab' | 'blank'
    right: 'flat' | 'tab' | 'blank'
    bottom: 'flat' | 'tab' | 'blank'
    left: 'flat' | 'tab' | 'blank'
  }
  difficulty: 'easy' | 'medium' | 'hard'
  region: 'subject' | 'background'
  // Optional properties for enhanced rendering
  edgeOffsets?: { left: number, top: number, right: number, bottom: number }
  shapePath?: string
}

export interface PuzzleData {
  pieces: PuzzlePiece[]
  imageUrl: string
  difficulty: string
  estimatedSolveTime: number
  metadata?: {
    originalImageUrl?: string
    styleType?: string
    pieceCount: number
    createdAt: string
  }
}

export interface GameStats {
  completionTime: number
  hintsUsed: number
  score: number
  difficulty: string
  piecesMoved: number
  piecesRotated: number
}

export interface SaveData {
  puzzleId: string
  pieces: PuzzlePiece[]
  gameTime: number
  hintsUsed: number
  score: number
  lastSaved: string
}

// Base puzzle piece type from API (without enhanced properties)
export interface BasePuzzlePiece {
  id: string
  x: number
  y: number
  width: number
  height: number
  rotation: number
  imageData: string
  correctPosition: { x: number, y: number }
  currentPosition: { x: number, y: number }
  isPlaced: boolean
  isSelected: boolean
  edges: {
    top: 'flat' | 'tab' | 'blank'
    right: 'flat' | 'tab' | 'blank'
    bottom: 'flat' | 'tab' | 'blank'
    left: 'flat' | 'tab' | 'blank'
  }
  difficulty: 'easy' | 'medium' | 'hard'
  region: 'subject' | 'background'
}

// Base puzzle data from API
export interface BasePuzzleData {
  pieces: BasePuzzlePiece[]
  imageUrl: string
  difficulty: string
  estimatedSolveTime: number
  metadata?: {
    originalImageUrl?: string
    styleType?: string
    pieceCount: number
    createdAt: string
  }
}

// Utility function to enhance base puzzle pieces with additional properties
export const enhancePuzzlePieces = (basePieces: BasePuzzlePiece[]): PuzzlePiece[] => {
  return basePieces.map((piece, index) => ({
    ...piece,
    zIndex: index,
    connectedPieces: []
  }))
}

// Utility function to enhance base puzzle data
export const enhancePuzzleData = (baseData: BasePuzzleData): PuzzleData => {
  return {
    ...baseData,
    pieces: enhancePuzzlePieces(baseData.pieces)
  }
}
