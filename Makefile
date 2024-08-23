build_image:
	@echo "Building animate docker image..."
	@docker buildx build -t ai.animate -f Dockerfile .
	@echo "Build finished"

gen_grpc:
	@echo "Generating grpc files..."
	@python -m grpc_tools.protoc -I./server/proto --python_out=./server/rpc --grpc_python_out=./server/rpc ./server/proto/animate_service.proto
	@echo "Generation finished"